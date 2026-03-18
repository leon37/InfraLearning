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
		Cloneflags: syscall.CLONE_NEWNS,
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

	err = syscall.Mount("anything", "/tmp/mnt-test", "tmpfs", uintptr(0), "")
	if err != nil {
		log.Fatalf("mount err %v", err)
		return
	}

	cmd := "/bin/sh"
	argv := []string{cmd}
	if err := syscall.Exec(cmd, argv, os.Environ()); err != nil {
		log.Fatalf("变身 sh 失败: %v", err)
	}
}
