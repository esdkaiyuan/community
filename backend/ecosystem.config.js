module.exports = {
  apps: [
    {
      name: 'community-backend',
      script: './server.js',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PORT: 5000
      },
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000,
      cron_restart: '0 0 * * *',
      kill_timeout: 5000,
      listen_timeout: 10000
    },
    {
      // 每天凌晨 3:30 清扫上传目录里的孤儿封面（选了图但没提交的那类）。
      // autorestart:false —— 脚本跑完即退出，靠 cron_restart 每天唤醒一次；
      // 这是 PM2 跑定时任务的标准姿势，比单开一份 crontab 更好维护。
      name: 'community-uploads-prune',
      script: './scripts/prune-uploads.js',
      args: '--apply',
      instances: 1,
      exec_mode: 'fork',
      autorestart: false,
      watch: false,
      cron_restart: '30 3 * * *',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/prune.err.log',
      out_file: './logs/prune.out.log',
      merge_logs: true
    },
    {
      // 每天凌晨 4:00 按留存期清理操作日志（默认 365 天）。
      // 同样用 autorestart:false + cron_restart 唤醒 —— 每个 app 有自己的
      // cron_restart，互不影响，所以可以和上面的上传清扫各挂各的。
      name: 'community-logs-prune',
      script: './scripts/prune-activity-logs.js',
      args: '--apply',
      instances: 1,
      exec_mode: 'fork',
      autorestart: false,
      watch: false,
      cron_restart: '0 4 * * *',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/prune-logs.err.log',
      out_file: './logs/prune-logs.out.log',
      merge_logs: true
    }
  ]
}
