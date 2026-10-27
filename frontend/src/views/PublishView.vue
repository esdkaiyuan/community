<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <div class="mb-8">
      <h1 class="font-display text-title1 font-semibold tracking-tight text-ink sm:text-largetitle">发布项目</h1>
      <p class="mt-2 text-footnote text-ink-mid">把你的想法写下来，让志同道合的人找到你。</p>
    </div>

    <ProjectForm mode="create" />
  </div>
</template>

<script setup>
import ProjectForm from '@/components/ProjectForm.vue'
</script>
