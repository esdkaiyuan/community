<template>
  <!-- 发布 / 编辑共用表单：一处维护校验、标签输入与封面预览 -->
  <form class="card space-y-6 p-6 sm:p-8" data-test="project-form" @submit.prevent="handleSubmit">
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

    <!-- 分类（线上 category_id 为 NOT NULL，必选） -->
    <div>
      <label class="form-label">
        项目分类 <span class="text-clay">*</span>
      </label>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="cat in categories"
          :key="cat.id"
          type="button"
          class="cat-pill"
          :class="{ 'is-active': form.categoryId === cat.id }"
          data-test="category-option"
          :aria-pressed="form.categoryId === cat.id"
          @click="form.categoryId = cat.id"
        >
          <AppIcon v-if="cat.icon" :name="categoryIcon(cat.icon)" class="h-3.5 w-3.5" />
          {{ cat.name }}
        </button>
      </div>
      <p v-if="errors.categoryId" class="form-error" data-test="error-category">{{ errors.categoryId }}</p>
      <p v-else class="mt-1.5 text-xs text-ink-dim">分类决定项目出现在广场的哪一栏，选最贴近的一个即可。</p>
    </div>

    <!-- 介绍 -->
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
      <label class="form-label" for="tag">
        标签 <span class="text-xs font-normal text-ink-dim">（最多 {{ TAG_MAX_COUNT }} 个，回车添加）</span>
      </label>
      <div class="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-cream px-3 py-2 transition-all focus-within:border-pine focus-within:ring-4 focus-within:ring-pine/10">
        <span v-for="(tag, i) in form.tags" :key="tag" class="chip !py-1" data-test="selected-tag">
          # {{ tag }}
          <button
            type="button"
            class="ml-1 text-ink-dim transition-colors hover:text-clay"
            data-test="remove-tag"
            :aria-label="`移除标签 ${tag}`"
            @click="form.tags.splice(i, 1)"
          >
            <AppIcon name="x" class="h-3 w-3" />
          </button>
        </span>
        <input
          id="tag"
          v-model.trim="tagInput"
          data-test="tag-input"
          type="text"
          class="min-w-[8rem] flex-1 bg-transparent py-1 text-sm outline-none placeholder:text-ink-dim"
          :placeholder="form.tags.length ? '' : '例如：环保、开源、线下活动'"
          :maxlength="TAG_MAX_LENGTH"
          :disabled="form.tags.length >= TAG_MAX_COUNT"
          @keydown.enter.prevent="addTagFromInput"
          @keydown.backspace="onTagBackspace"
        />
      </div>

      <!-- 快捷选择：热门标签（有数据时）+ 冷启动候选池 -->
      <div v-if="showSuggestions" class="mt-2.5">
        <p class="mb-1.5 text-xs text-ink-dim">试试这些常被搜索的标签，点一下就加上：</p>
        <div class="flex flex-wrap gap-2" data-test="tag-suggestions">
          <button
            v-for="name in suggestedTags"
            :key="name"
            type="button"
            class="chip-link !py-1 cursor-pointer"
            data-test="tag-suggestion"
            @click="addTag(name)"
          >
            # {{ name }}
          </button>
        </div>
      </div>
      <p v-else class="mt-1.5 text-xs text-ink-dim">
        标签会进入广场的「热门标签」，是别人发现你这个项目的主要入口。
      </p>
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
      <p v-if="coverBroken && form.coverImage" class="form-error">图片链接无法加载，保存后将显示默认封面</p>
      <p v-else class="mt-1.5 text-xs text-ink-dim">不填也没关系，我们会为你生成一个漂亮的默认封面。</p>
    </div>

    <!-- 提交 -->
    <div class="flex items-center justify-end gap-3 border-t border-line pt-6">
      <button type="button" class="btn-ghost" @click="handleCancel">
        {{ isEdit ? '放弃修改' : '取消' }}
      </button>
      <button type="submit" class="btn-primary !px-8 !py-3" :disabled="submitting" data-test="submit-project">
        <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
          <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
        <AppIcon v-else :name="isEdit ? 'pencil' : 'sprout'" class="h-4 w-4" />
        {{ submitText }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createProject, updateProject, getProjectTags } from '@/api/project'
import { getCategories } from '@/api/category'
import { categoryIcon } from '@/utils/categoryIcon'
import { stripEmoji } from '@/utils/text'
import { TAG_MAX_COUNT, TAG_MAX_LENGTH, DEFAULT_TAG_SUGGESTIONS, addTagToList, cleanTag, toTagList } from '@/utils/tags'
import AppIcon from '@/components/AppIcon.vue'
import { toast } from '@/composables/useToast'

const props = defineProps({
  mode: { type: String, default: 'create' }, // create | edit
  project: { type: Object, default: null } // edit 模式下用于回填
})

const emit = defineEmits(['submitted'])

const router = useRouter()
const isEdit = computed(() => props.mode === 'edit')

const categories = ref([])
const popularTags = ref([])
const form = reactive({
  title: props.project?.title || '',
  description: props.project?.description || '',
  categoryId: props.project?.categoryId ?? null,
  tags: toTagList(props.project?.tags),
  coverImage: props.project?.coverImage || ''
})
const errors = reactive({ title: '', description: '', categoryId: '' })
const tagInput = ref('')
const coverBroken = ref(false)
const submitting = ref(false)

const submitText = computed(() => {
  if (submitting.value) return isEdit.value ? '保存中…' : '发布中…'
  return isEdit.value ? '保存修改' : '发布项目'
})

// 快捷标签：热门标签在前，不够用冷启动候选池补齐，已选中的不重复出现
//
// 热门标签的门槛：至少被 2 个项目用过、且长度 ≥ 2。
// 只被一个项目用过的标签算不上「热门」——把它摆成候选会给人虚假的权威感，
// 也容易把一次性的随手标签（单字、测试残留之类）推荐给所有人。
const SUGGEST_MIN_COUNT = 2
const SUGGEST_MIN_LENGTH = 2

const suggestedTags = computed(() => {
  const used = new Set(form.tags.map((t) => t.toLowerCase()))
  const out = []
  const push = (raw, minLength = 1) => {
    const name = cleanTag(raw)
    const key = name.toLowerCase()
    if (!name || used.has(key) || name.length < minLength) return
    used.add(key)
    out.push(name)
  }
  popularTags.value
    .filter((t) => (t.count || 0) >= SUGGEST_MIN_COUNT)
    .forEach((t) => push(t.name, SUGGEST_MIN_LENGTH))
  DEFAULT_TAG_SUGGESTIONS.forEach((name) => push(name))
  return out.slice(0, 8)
})
const showSuggestions = computed(
  () => form.tags.length < TAG_MAX_COUNT && suggestedTags.value.length > 0
)

const addTag = (raw) => {
  const next = addTagToList(form.tags, raw)
  if (next !== form.tags) form.tags = next
}

const addTagFromInput = () => {
  const raw = tagInput.value
  if (!raw) return
  addTag(raw)
  tagInput.value = ''
}

// 输入框为空时按退格删除最后一个标签
const onTagBackspace = () => {
  if (!tagInput.value && form.tags.length) form.tags.pop()
}

const validate = () => {
  errors.title = form.title.length >= 4 ? '' : '标题至少 4 个字符'
  errors.categoryId = form.categoryId ? '' : '请选择一个项目分类'
  errors.description = form.description.length >= 20 ? '' : '介绍至少 20 个字符，多写一点更容易吸引伙伴'
  return !errors.title && !errors.categoryId && !errors.description
}

const handleCancel = () => {
  if (isEdit.value) router.push(`/project/${props.project.id}`)
  else router.back()
}

const handleSubmit = async () => {
  addTagFromInput() // 提交前收纳未回车的标签
  if (!validate() || submitting.value) return

  // 全站仅允许矢量图标：提交前移除标题与介绍中的 emoji
  const cleanedTitle = stripEmoji(form.title)
  const cleanedDescription = stripEmoji(form.description)
  const hadEmoji = cleanedTitle !== form.title.trim() || cleanedDescription !== form.description.trim()
  if (hadEmoji) {
    form.title = cleanedTitle
    form.description = cleanedDescription
    if (!validate()) return
  }

  submitting.value = true
  try {
    const payload = {
      title: form.title,
      description: form.description,
      categoryId: form.categoryId,
      tags: form.tags,
      coverImage: coverBroken.value ? '' : form.coverImage
    }
    const res = isEdit.value
      ? await updateProject(props.project.id, payload)
      : await createProject(payload)

    const suffix = hadEmoji ? '（表情符号已自动移除）' : ''
    toast(isEdit.value ? `项目已更新${suffix}` : `项目发布成功${suffix}！`)
    emit('submitted', res.data)
    router.push(`/project/${res.data.id}`)
  } catch {
    // 错误已由拦截器 toast
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  // 分类与热门标签各自独立，任何一个失败都不该挡住发布
  getCategories()
    .then((res) => {
      categories.value = res.data
    })
    .catch(() => {})
  getProjectTags()
    .then((res) => {
      popularTags.value = res.data || []
    })
    .catch(() => {})
})
</script>
