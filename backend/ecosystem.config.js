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
    }
  ]
}
