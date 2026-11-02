<template>
  <div class="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    <nav class="mb-4 flex items-center gap-1.5 text-footnote text-ink-dim">
      <router-link to="/" class="transition-colors hover:text-pine">项目广场</router-link>
      <span>/</span>
      <span class="text-ink-mid">发布项目</span>
    </nav>

    <ProjectForm mode="create" />

    <p class="mt-5 text-center font-mono text-caption2 uppercase tracking-[0.14em] text-ink-dim">
      // ONE IDEA, ONE CO-CREATOR
    </p>
  </div>
</template>

<script setup>
import ProjectForm from '@/components/ProjectForm.vue'
</script>
