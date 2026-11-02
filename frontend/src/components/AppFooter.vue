<template>
  <footer class="mt-20 border-t border-line/70 bg-paper">
    <div class="site-shell py-12 sm:py-14">
      <div class="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_repeat(4,minmax(0,0.55fr))]">
        <!-- 品牌 -->
        <div>
          <div class="flex items-center gap-3">
            <span class="sketch-mark flex h-9 w-9 items-center justify-center">
              <svg viewBox="0 0 64 64" class="h-5 w-5" aria-hidden="true">
                <path d="M32 46c0-9 0-14 0-19" stroke="rgb(var(--c-ink))" stroke-width="4" stroke-linecap="round" fill="none" />
                <path d="M32 30c0-7 5-11.5 11.5-11.5C43.5 25.5 38.5 30 32 30z" fill="rgb(var(--c-pine) / 0.55)" />
                <path d="M32 36c0-5.6-4.2-9.5-9.5-9.5 0 5.6 4.2 9.5 9.5 9.5z" fill="rgb(var(--c-pine))" />
              </svg>
            </span>
            <div class="leading-none">
              <p class="font-brand text-[20px] font-semibold tracking-tight text-ink">共创社区</p>
              <p class="mt-1.5 font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-ink-dim">Co-Creation Community</p>
            </div>
          </div>
          <p class="mt-5 max-w-sm text-footnote leading-relaxed text-ink-mid">
            连接想法与能力，让每一个好创意都能找到同行者。发布项目、参与共创，一起把想法变成现实。
          </p>
          <p class="mt-3 font-mono text-caption2 uppercase tracking-[0.16em] text-ink-dim">// Always building · Open collaboration</p>
        </div>

        <div>
          <p class="font-mono text-caption1 font-semibold uppercase tracking-[0.16em] text-ink-dim">// 探索</p>
          <ul class="mt-4 space-y-2.5 text-footnote text-ink-mid">
            <li><router-link to="/" class="transition-colors hover:text-pine">项目广场</router-link></li>
            <li><router-link to="/?filter=recommend" class="transition-colors hover:text-pine">编辑推荐</router-link></li>
            <li><router-link to="/?sort=trending" class="transition-colors hover:text-pine">本周热门</router-link></li>
          </ul>
        </div>

        <div>
          <p class="font-mono text-caption1 font-semibold uppercase tracking-[0.16em] text-ink-dim">// 参与</p>
          <ul class="mt-4 space-y-2.5 text-footnote text-ink-mid">
            <li><router-link to="/publish" class="transition-colors hover:text-pine">发布项目</router-link></li>
            <li><router-link to="/register" class="transition-colors hover:text-pine">加入社区</router-link></li>
            <li><router-link to="/login" class="transition-colors hover:text-pine">登录</router-link></li>
          </ul>
        </div>

        <div>
          <p class="font-mono text-caption1 font-semibold uppercase tracking-[0.16em] text-ink-dim">// 账号</p>
          <ul class="mt-4 space-y-2.5 text-footnote text-ink-mid">
            <li><router-link to="/profile" class="transition-colors hover:text-pine">个人中心</router-link></li>
            <li><router-link to="/notifications" class="transition-colors hover:text-pine">通知</router-link></li>
            <li><router-link to="/security" class="transition-colors hover:text-pine">账号安全</router-link></li>
            <li><router-link to="/appearance" class="transition-colors hover:text-pine" data-test="appearance-footer">外观设置</router-link></li>
          </ul>
        </div>

        <div>
          <p class="font-mono text-caption1 font-semibold uppercase tracking-[0.16em] text-ink-dim">// 规则与帮助</p>
          <ul class="mt-4 space-y-2.5 text-footnote text-ink-mid">
            <li><router-link to="/terms" class="transition-colors hover:text-pine">用户协议</router-link></li>
            <li><router-link to="/privacy" class="transition-colors hover:text-pine">隐私政策</router-link></li>
            <li><router-link to="/community-rules" class="transition-colors hover:text-pine">平台管理条例</router-link></li>
            <li><router-link to="/help" class="transition-colors hover:text-pine">帮助中心</router-link></li>
          </ul>
        </div>
      </div>

      <div class="mt-12 flex flex-col gap-3 border-t border-line/70 pt-6 text-caption1 text-ink-dim sm:flex-row sm:items-center sm:justify-between">
        <p>© {{ year }} 共创社区 · 一起想，一起做</p>
        <p class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>内容由社区成员发布</span>
          <span aria-hidden="true">·</span>
          <router-link to="/community-rules" class="transition-colors hover:text-pine">平台管理条例</router-link>
          <span aria-hidden="true">·</span>
          <router-link to="/community-rules#report" class="transition-colors hover:text-pine">举报与申诉</router-link>
        </p>
      </div>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear()
</script>