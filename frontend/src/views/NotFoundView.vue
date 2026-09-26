<template>
  <div class="flex flex-col items-center justify-center px-4 py-24 text-center">
    <!-- 苹果官网式渐变大字 -->
    <p
      class="bg-gradient-to-b from-ink to-ink-mid bg-clip-text font-display text-8xl font-semibold tracking-tight text-transparent sm:text-9xl"
      aria-hidden="true"
    >
      404
    </p>
    <h1 class="mt-4 text-2xl font-semibold tracking-tight text-ink">这片土地还没被开垦</h1>
    <p class="mt-2 max-w-sm text-sm leading-relaxed text-ink-mid">
      你访问的页面不存在或已被移动。回到项目广场，看看正在发生的共创吧。
    </p>
    <router-link to="/" class="btn-primary mt-8">回到首页</router-link>
  </div>
</template>
