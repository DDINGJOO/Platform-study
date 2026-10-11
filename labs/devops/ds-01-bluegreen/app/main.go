// 배포 전략 실습용 웹 서버.
// 응답 본문에 버전을 돌려주고, 기동 지연과 종료 동작을 환경변수로 바꾼다.
//
//	VERSION        응답에 실을 버전 문자열 (기본 v1)
//	STARTUP_DELAY  준비 완료까지 걸리는 시간. 그동안 /ready 는 503 (기본 10s)
//	WORK_MS        요청 하나를 처리하는 시간 (기본 20)
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync/atomic"
	"syscall"
	"time"
)

func env(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func main() {
	version := env("VERSION", "v1")
	delay, _ := time.ParseDuration(env("STARTUP_DELAY", "10s"))
	workMs, _ := strconv.Atoi(env("WORK_MS", "20"))
	host, _ := os.Hostname()

	var ready atomic.Bool
	started := time.Now()
	go func() {
		time.Sleep(delay) // JVM 워밍업, 캐시 적재 같은 기동 비용을 흉내 낸다
		ready.Store(true)
		log.Printf("ready version=%s after=%s", version, time.Since(started).Round(time.Millisecond))
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(time.Duration(workMs) * time.Millisecond)
		fmt.Fprintf(w, "%s %s\n", version, host)
	})
	mux.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		if !ready.Load() {
			http.Error(w, "warming up", http.StatusServiceUnavailable)
			return
		}
		fmt.Fprintln(w, "ok")
	})

	srv := &http.Server{Addr: ":8080", Handler: mux}
	go func() {
		if err := srv.ListenAndServe(); err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()
	log.Printf("listening version=%s", version)

	// SIGTERM 을 받으면 새 연결을 받지 않고, 처리 중인 요청만 끝내고 내려간다.
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGTERM, syscall.SIGINT)
	<-sig
	log.Printf("SIGTERM version=%s", version)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(ctx)
	log.Printf("stopped version=%s", version)
}
