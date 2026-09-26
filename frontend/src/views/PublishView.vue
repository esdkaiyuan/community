<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <div class="mb-8">
      <h1 class="font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">发布项目</h1>
      <p class="mt-2 text-sm text-ink-mid">把你的想法写下来，让志同道合的人找到你。</p>
    </div>

    <form class="card space-y-6 p-6 sm:p-8" @submit.prevent="handleSubmit">
      <!-- 标题 -->
      <div>
        <label class="form-label" for="title">
          项目标题 <span class="text-clay">*</span>
        </label>
        <input
          id="title"
          v-model.trim="form.title"
          type="text"
          class="input"
          placeholder="一句话说清你的项目，例如：社区旧物改造工作坊"
          maxlength="60"
        />
        <div class="mt-1.5 flex items-center justify-between">
          <p v-if="errors.title" class="form-error !mt-0">{{ errors.title }}</p>
          <span class="ml-auto text-xs text-ink-dim">{{ form.title.length }}/60</span>
        </div>
      </div>

      <!-- 分类 -->
      <div>
        <label class="form-label">项目分类</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="cat in categories"
            :key="cat.id"
            type="button"
            class="cat-pill"
            :class="{ 'is-active': form.categoryId === cat.id }"
            @click="form.categoryId = form.categoryId === cat.id ? null : cat.id"
          >
            <AppIcon v-if="cat.icon" :name="categoryIcon(cat.icon)" class="h-3.5 w-3.5" />
            {{ cat.name }}
          </button>
        </div>
      </div>

      <!-- 描述 -->
      <div>
        <label class="form-label" for="description">
          项目介绍 <span class="text-clay">*</span>
        </label>
        <textarea
          id="description"
          v-model.trim="form.description"
          class="input min-h-[180px] resize-y leading-relaxed"
          placeholder="介绍一下：你想做什么？为什么想做？目前进展如何？需要什么样的伙伴？"
          maxlength="2000"
        ></textarea>
        <div class="mt-1.5 flex items-center justify-between">
          <p v-if="errors.description" class="form-error !mt-0">{{ errors.description }}</p>
          <span class="ml-auto text-xs text-ink-dim">{{ form.description.length }}/2000</span>
        </div>
      </div>

      <!-- 标签 -->
      <div>
        <label class="form-label" for="tag">标签 <span class="text-xs font-normal text-ink-dim">（最多 5 个，回车添加）</span></label>
        <div class="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 transition-all focus-within:border-pine focus-within:ring-4 focus-within:ring-pine/10">
          <span
            v-for="(tag, i) in form.tags"
            :key="tag"
            class="chip !py-1"
          >
            # {{ tag }}
            <button type="button" class="ml-1 text-ink-dim transition-colors hover:text-clay" aria-label="移除标签" @click="form.tags.splice(i, 1)">
              <AppIcon name="x" class="h-3 w-3" />
            </button>
          </span>
          <input
            id="tag"
            v-model.trim="tagInput"
            type="text"
            class="min-w-[8rem] flex-1 bg-transparent py-1 text-sm outline-none placeholder:text-ink-dim"
            :placeholder="form.tags.length ? '' : '例如：环保、开源、线下活动'"
            maxlength="12"
            :disabled="form.tags.length >= 5"
            @keydown.enter.prevent="addTag"
            @keydown.backspace="onTagBackspace"
          />
        </div>
      </div>

      <!-- 封面 -->
      <div>
        <label class="form-label" for="cover">封面图片链接 <span class="text-xs font-normal text-ink-dim">（选填）</span></label>
        <input
          id="cover"
          v-model.trim="form.coverImage"
          type="url"
          class="input"
          placeholder="https://example.com/cover.jpg"
        />
        <div v-if="form.coverImage" class="mt-3 overflow-hidden rounded-xl border border-line">
          <img
            :src="form.coverImage"
            alt="封面预览"
            class="aspect-[16/9] w-full object-cover"
            @error="coverBroken = true"
            @load="coverBroken = false"
          />
        </div>
        <p v-if="coverBroken && form.coverImage" class="form-error">图片链接无法加载，发布后将显示默认封面</p>
        <p v-else class="mt-1.5 text-xs text-ink-dim">不填也没关系，我们会为你生成一个漂亮的默认封面。</p>
      </div>

      <!-- 提交 -->
      <div class="flex items-center justify-end gap-3 border-t border-line pt-6">
        <button type="button" class="btn-ghost" @click="router.back()">取消</button>
        <button type="submit" class="btn-primary !px-8 !py-3" :disabled="submitting">
          <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
            <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
          </svg>
          <AppIcon v-if="!submitting" name="sprout" class="h-4 w-4" />
          {{ submitting ? '发布中…' : '发布项目' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createProject } from '@/api/project'
import { getCategories } from '@/api/category'
import { categoryIcon } from '@/utils/categoryIcon'
import AppIcon from '@/components/AppIcon.vue'
import { toast } from '@/composables/useToast'

const router = useRouter()

const categories = ref([])
const form = reactive({
  title: '',
  description: '',
  categoryId: null,
  tags: [],
  coverImage: ''
})
const errors = reactive({ title: '', description: '' })
const tagInput = ref('')
const coverBroken = ref(false)
const submitting = ref(false)

const addTag = () => {
  const tag = tagInput.value.trim()
  if (!tag) return
  if (form.tags.includes(tag)) {
    tagInput.value = ''
    return
  }
  if (form.tags.length >= 5) return
  form.tags.push(tag)
  tagInput.value = ''
}

// 输入框为空时按退格删除最后一个标签
const onTagBackspace = () => {
  if (!tagInput.value && form.tags.length) form.tags.pop()
}

const validate = () => {
  errors.title = form.title.length >= 4 ? '' : '标题至少 4 个字符'
  errors.description = form.description.length >= 20 ? '' : '介绍至少 20 个字符，多写一点更容易吸引伙伴'
  return !errors.title && !errors.description
}

const handleSubmit = async () => {
  addTag() // 提交前收纳未回车的标签
  if (!validate() || submitting.value) return
  submitting.value = true
  try {
    const res = await createProject({
      title: form.title,
      description: form.description,
      categoryId: form.categoryId,
      tags: form.tags,
      coverImage: coverBroken.value ? '' : form.coverImage
    })
    toast('项目发布成功！')
    router.push(`/project/${res.data.id}`)
  } catch {
    // 错误已由拦截器 toast
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const res = await getCategories()
    categories.value = res.data
  } catch {
    // 分类加载失败时仍可发布（不选分类）
  }
})
</script>

