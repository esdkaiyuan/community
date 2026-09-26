<template>
  <footer class="mt-16 border-t border-line bg-cream">
    <div class="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div class="flex flex-col items-start justify-between gap-8 md:flex-row md:items-center">
        <div>
          <div class="flex items-center gap-2.5">
            <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-pine">
              <svg viewBox="0 0 64 64" class="h-4.5 w-4.5" aria-hidden="true">
                <path d="M32 46c0-9 0-14 0-19" stroke="#F7F4EC" stroke-width="4" stroke-linecap="round" fill="none" />
                <path d="M32 30c0-7 5-11.5 11.5-11.5C43.5 25.5 38.5 30 32 30z" fill="#A8CF8E" />
                <path d="M32 36c0-5.6-4.2-9.5-9.5-9.5 0 5.6 4.2 9.5 9.5 9.5z" fill="#F7F4EC" />
              </svg>
            </span>
            <span class="font-display text-base font-bold text-ink">共创社区</span>
          </div>
          <p class="mt-3 max-w-sm text-sm leading-relaxed text-ink-mid">
            连接想法与能力，让每一个好创意都能找到同行者。发布项目、参与共创，一起把想法变成现实。
          </p>
        </div>

        <div class="flex gap-14 text-sm">
          <div>
            <p class="mb-3 font-medium text-ink">探索</p>
            <ul class="space-y-2 text-ink-mid">
              <li><router-link to="/" class="transition-colors hover:text-pine">项目广场</router-link></li>
              <li><router-link to="/?filter=recommend" class="transition-colors hover:text-pine">编辑推荐</router-link></li>
              <li><router-link to="/?filter=hot" class="transition-colors hover:text-pine">热门项目</router-link></li>
            </ul>
          </div>
          <div>
            <p class="mb-3 font-medium text-ink">参与</p>
            <ul class="space-y-2 text-ink-mid">
              <li><router-link to="/publish" class="transition-colors hover:text-pine">发布项目</router-link></li>
              <li><router-link to="/register" class="transition-colors hover:text-pine">加入社区</router-link></li>
            </ul>
          </div>
        </div>
      </div>

      <div class="mt-10 border-t border-line pt-5 text-xs text-ink-dim">
        © {{ year }} 共创社区 · 一起想，一起做
      </div>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear()
</script>
