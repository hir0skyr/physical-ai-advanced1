import argparse, json, math, os, pickle
import torch
import genesis as gs
from rsl_rl.runners import OnPolicyRunner
from go2_env import Go2Env

WAYPOINTS = [(3.0, 0.0), (3.0, 3.0), (0.0, 3.0), (0.0, 0.0)]
ARRIVE_R = 0.3
V_MAX, W_MAX, K_YAW = 0.6, 1.0, 1.5   # 学習した指令範囲の内側に収める


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def yaw_of(q):  # Genesisのクォータニオンは (w, x, y, z)
    w, x, y, z = [float(v) for v in q]
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def nav_command(pos, quat, wp):
    dx, dy = wp[0] - float(pos[0]), wp[1] - float(pos[1])
    dist = math.hypot(dx, dy)
    err = wrap(math.atan2(dy, dx) - yaw_of(quat))
    wz = max(-W_MAX, min(W_MAX, K_YAW * err))
    vx = V_MAX * max(0.0, math.cos(err)) * min(1.0, dist / 0.8)  # 向きがずれるほど減速、接近でも減速
    vx = max(vx, 0.1)  # 0指令は学習で稀なので下限を設ける
    return (vx, 0.0, wz), dist


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-e", "--exp-name", default="go2-v1")
    p.add_argument("--ckpt", type=int, required=True)
    p.add_argument("--laps", type=int, default=2)
    p.add_argument("--max-time", type=float, default=90.0)
    p.add_argument("--push-at", type=float, nargs="*", default=[])   # 押す時刻[s]
    p.add_argument("--push-vel", type=float, nargs=2, default=[0.0, 0.5])
    p.add_argument("--cmd", type=float, nargs=3, default=None)       # 固定指令デバッグ用 vx vy wz
    p.add_argument("--record", default=None)                         # 例: out/v2.mp4
    p.add_argument("--cam", choices=["follow", "top"], default="follow")
    p.add_argument("--viewer", action="store_true")
    args = p.parse_args()

    gs.init(backend=gs.gpu, precision="32", logging_level="warning")
    log_dir = f"logs/{args.exp_name}"
    env_cfg, obs_cfg, reward_cfg, command_cfg, train_cfg = pickle.load(open(f"{log_dir}/cfgs.pkl", "rb"))
    env_cfg.update(episode_length_s=1e4, push_interval_s=0.0,
                   termination_if_roll_greater_than=1e3, termination_if_pitch_greater_than=1e3)
    reward_cfg["reward_scales"] = {}

    env = Go2Env(num_envs=1, env_cfg=env_cfg, obs_cfg=obs_cfg, reward_cfg=reward_cfg,
                 command_cfg=command_cfg, show_viewer=args.viewer,
                 waypoints=WAYPOINTS, record=args.record is not None)
    runner = OnPolicyRunner(env, train_cfg, log_dir, device=gs.device)
    runner.load(os.path.join(log_dir, f"model_{args.ckpt}.pt"))
    policy = runner.get_inference_policy(device=gs.device)

    cam = env.cam
    env.reset()
    if cam:
        os.makedirs(os.path.dirname(args.record) or ".", exist_ok=True)
        cam.start_recording(save_to_filename=args.record, fps=25)
        if args.cam == "top":
            cam.set_pose(pos=(1.5, 0.5, 6.5), lookat=(1.5, 1.5, 0.0))

    wp_i, laps, reached, pushes = 0, 0, [], []
    push_times = sorted(args.push_at)
    err_v, err_w, fell = [], [], False
    n_steps = int(args.max_time / env.dt)

    with torch.no_grad():
        for step in range(n_steps):
            t = step * env.dt
            pos, quat = env.base_pos[0], env.base_quat[0]

            if args.cmd:
                cmd = tuple(args.cmd)
            else:
                cmd, dist = nav_command(pos, quat, WAYPOINTS[wp_i])
                if dist < ARRIVE_R:
                    reached.append(round(t, 2))
                    wp_i += 1
                    if wp_i == len(WAYPOINTS):
                        wp_i, laps = 0, laps + 1
                        if laps >= args.laps:
                            break
                    cmd, _ = nav_command(pos, quat, WAYPOINTS[wp_i])

            while push_times and t >= push_times[0]:
                push_times.pop(0)
                pushes.append(round(t, 2))
                env.apply_push(torch.tensor([args.push_vel], dtype=gs.tc_float, device=gs.device))

            # 指令を上書きして観測を作り直す（stepの内部で乱数指令に更新されるため）
            env.commands[0] = torch.tensor(cmd, dtype=gs.tc_float, device=gs.device)
            env._update_observation()
            actions = policy(env.get_observations())
            env.step(actions)

            err_v.append(abs(cmd[0] - float(env.base_lin_vel[0, 0])))
            err_w.append(abs(cmd[2] - float(env.base_ang_vel[0, 2])))
            if max(abs(float(env.base_euler[0, 0])), abs(float(env.base_euler[0, 1]))) > 45:
                fell = True
                break

            if cam and args.cam == "follow":   # 描画はscene.step()が25fpsで自動的に行う
                x, y = float(env.base_pos[0, 0]), float(env.base_pos[0, 1])
                cam.set_pose(pos=(x - 2.0, y - 2.0, 1.5), lookat=(x, y, 0.3))

    if cam:
        cam.stop_recording()

    after_push = [r for r in reached if pushes and r > pushes[0]]
    res = dict(exp=args.exp_name, ckpt=args.ckpt,
               reached=len(reached), target=args.laps * len(WAYPOINTS), reach_times=reached,
               fell=fell, pushes=pushes, reached_after_push=len(after_push),
               mean_vx_err=sum(err_v) / max(1, len(err_v)), mean_wz_err=sum(err_w) / max(1, len(err_w)))
    os.makedirs("results", exist_ok=True)
    json.dump(res, open(f"results/{args.exp_name}_{args.ckpt}.json", "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()