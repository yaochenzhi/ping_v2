package main

import (
    "fmt"
    "log"
    "sync"
    "os/exec"
    "syscall"
    "runtime"
    "database/sql"
    _ "github.com/go-sql-driver/mysql"
)


var wg sync.WaitGroup


var (
  MaxWorker = runtime.NumCPU()
)


func init() {
  runtime.GOMAXPROCS(MaxWorker)
}


func get_hosts()([]string) {

    all_hosts := make([]string, 0)

    db, err := sql.Open("mysql", "t:t@tcp(h:3306)/ping")

    if err != nil {
        panic(err.Error())
    }

    defer db.Close()

    hosts, err := db.Query("select ip_addr from ping_ip_addr_list_tb where is_active = 1 ")

    if err != nil {
        panic(err.Error())
    }

    defer hosts.Close()

    var host string

    for hosts.Next() {
        
        err = hosts.Scan(&host)

        if err != nil {
            panic(err.Error())
        }

        all_hosts = append(all_hosts, host)

    }
    
    return all_hosts
}


func ping_host(queue chan HostStatus, host string){

    host_status := 0

    cmd := exec.Command("ping", "-c", "10", "-w", "10", host)

    if err := cmd.Start(); err != nil {
        log.Fatalf("cmd.Start: %v", err)
    }

    if err := cmd.Wait(); err != nil {
        if exiterr, ok := err.(*exec.ExitError); ok {

            if status, ok := exiterr.Sys().(syscall.WaitStatus); ok {
                host_status = status.ExitStatus()
            }
        } else {
            log.Fatalf("cmd.Wait: %v", err)
        }
    }

    queue <- HostStatus{host: host, status: host_status}
    
    wg.Done()
}


type HostStatus struct {
    host string
    status int
}


func main () {

    hosts := get_hosts()
        fmt.Println(len(hosts))
    queue := make(chan HostStatus, len(hosts))

    for _, host := range(get_hosts()) {
        wg.Add(1)
        go ping_host(queue, host)
    }

    wg.Wait()

    close(queue)

    for item := range queue{
        if item.status != 0{
            fmt.Println(item)
        }
    }

}
