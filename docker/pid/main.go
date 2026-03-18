package main

import (
	"log"
	"os"
	"os/exec"
	"syscall"
)

func main() {
	// 简单的路由：根据参数决定当前是“大爹”还是“儿子”
	if len(os.Args) < 2 {
		log.Fatalf("请指定命令, 例如: sudo ./my-container run")
	}

	switch os.Args[1] {
	case "run":
		parent()
	case "init":
		child()
	default:
		log.Fatalf("未知命令")
	}
}

// Parent: 运行在宿主机，负责劈开平行宇宙
func parent() {
	// /proc/self/exe 代表当前 Go 编译出的二进制文件本身
	// 这里相当于执行： ./my-container init
	cmd := exec.Command("/proc/self/exe", "init")

	// 赋予儿子隔离属性
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Cloneflags: syscall.CLONE_NEWPID | syscall.CLONE_NEWNS | syscall.CLONE_NEWUTS,
	}

	// 接住儿子的输入输出
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// 点火启动儿子，并等待它结束
	if err := cmd.Run(); err != nil {
		log.Fatalf("容器运行失败: %v", err)
	}
}

// Child: 运行在隔离的新宇宙中，负责装修（挂载），然后变身
func child() {
	// 1. 焊死车门：声明后续的挂载动作不传播回宿主机
	err := syscall.Mount("", "/", "", syscall.MS_PRIVATE|syscall.MS_REC, "")
	if err != nil {
		log.Fatalf("mount private err %v", err)
		return
	}

	// 2. 安全装修：挂载隔离的 /proc
	// 此时我们在隔离区，可以直接挂载，不需要再 Unmount 了
	err = syscall.Mount("proc", "/proc", "proc", uintptr(0), "")
	if err != nil {
		log.Fatalf("mount err %v", err)
		return
	}

	// 为了让你看效果，顺便改个名字
	err = syscall.Sethostname([]byte("my-isolated-container"))
	if err != nil {
		log.Fatalf("sethostname err %v", err)
		return
	}

	// 3. 终极变身 (Execve)：把当前 Go 进程彻底替换为 /bin/sh
	// 注意：这一步执行后，Go 代码就消失了，进程变成了 sh，但 PID 依然是 1！
	cmd := "/bin/sh"
	argv := []string{cmd}
	if err := syscall.Exec(cmd, argv, os.Environ()); err != nil {
		log.Fatalf("变身 sh 失败: %v", err)
	}
}
