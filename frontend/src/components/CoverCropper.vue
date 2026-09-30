<template>
  <div data-test="cover-crop">
    <!--
      取景框本身就是裁剪窗口：框里看到什么，裁完就留下什么。
      没有遮罩、没有可拖拽的把手 —— 少一层抽象，用户不用去理解
      「框外是暗的」和「框内是保留的」两者之间的关系。
    -->
    <div
      ref="frameEl"
      class="relative aspect-[16/9] w-full cursor-grab touch-none select-none overflow-hidden rounded-xl bg-ink/5 ring-1 ring-line active:cursor-grabbing"
      data-test="cover-crop-frame"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
    >
      <img
        ref="imgEl"
        :src="src"
        alt="封面裁剪预览"
        class="absolute left-0 top-0 max-w-none origin-top-left"
        :style="imgStyle"
        draggable="false"
        data-test="cover-crop-img"
        @load="onLoad"
        @error="onError"
      />

      <!-- 三分线：只帮用户找视觉重心，不参与任何几何计算 -->
      <div class="pointer-events-none absolute inset-0" aria-hidden="true">
        <div class="absolute left-1/3 top-0 h-full w-px bg-white/25" />
        <div class="absolute left-2/3 top-0 h-full w-px bg-white/25" />
        <div class="absolute left-0 top-1/3 h-px w-full bg-white/25" />
        <div class="absolute left-0 top-2/3 h-px w-full bg-white/25" />
      </div>

      <div
        v-if="!ready"
        class="absolute inset-0 flex items-center justify-center bg-black/25 text-xs text-white"
        data-test="cover-crop-loading"
      >
        正在准备…
      </div>
    </div>

    <div class="mt-3 flex items-center gap-3">
      <label class="flex flex-1 items-center gap-2 text-xs text-ink-dim" for="cover-crop-zoom">
        <AppIcon name="crop" class="h-4 w-4 shrink-0" />
        <span class="shrink-0">缩放</span>
        <input
          id="cover-crop-zoom"
          class="h-1 flex-1 cursor-pointer accent-pine disabled:cursor-not-allowed disabled:opacity-50"
          type="range"
          min="1"
          :max="COVER_CROP_MAX_ZOOM"
          step="0.05"
          :value="zoom"
          :disabled="locked || !ready"
          data-test="cover-crop-zoom"
          @input="onZoomInput"
        />
      </label>
      <button
        type="button"
        class="shrink-0 text-xs text-ink-dim transition-colors hover:text-ink disabled:opacity-50"
        data-test="cover-crop-center"
        :disabled="locked || !ready"
        @click="recenter"
      >
        居中
      </button>
    </div>

    <p class="mt-2 text-xs text-ink-dim">
      按住图片拖动即可调整位置。封面在列表里按 {{ COVER_ASPECT_LABEL }} 展示，框里留下什么就显示什么。
    </p>

    <div class="mt-3 flex items-center justify-end gap-3">
      <button
        type="button"
        class="btn-ghost"
        data-test="cover-crop-cancel"
        :disabled="locked"
        @click="emit('cancel')"
      >
        取消
      </button>
      <button
        type="button"
        class="btn-primary"
        data-test="cover-crop-confirm"
        :disabled="locked || !ready"
        @click="confirm"
      >
        <svg v-if="locked" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
          <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        </svg>
        <AppIcon v-else name="crop" class="h-4 w-4" />
        {{ busy ? '上传中…' : encoding ? '裁剪中…' : '完成裁剪' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  COVER_ASPECT_LABEL,
  COVER_CROP_MAX_ZOOM,
  centeredPan,
  clampPan,
  cropRegion,
  cropToFile,
  fitScale
} from '@/utils/imageCrop'
import { toast } from '@/composables/useToast'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  src: { type: String, required: true },
  // 上层正在把裁好的图传上去
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['done', 'cancel'])

const frameEl = ref(null)
const imgEl = ref(null)
const natural = ref({ w: 0, h: 0 })
const frame = ref({ w: 0, h: 0 })
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const encoding = ref(false)
const ready = ref(false)

const locked = computed(() => props.busy || encoding.value)

// zoom = 1 时图片恰好「铺满」取景框（短边对齐），这就是 object-cover 的行为
const baseScale = computed(() => fitScale(natural.value.w, natural.value.h, frame.value.w, frame.value.h))
const scale = computed(() => baseScale.value * Math.max(1, zoom.value))
const disp = computed(() => ({ w: natural.value.w * scale.value, h: natural.value.h * scale.value }))

const imgStyle = computed(() => ({
  width: `${disp.value.w}px`,
  height: `${disp.value.h}px`,
  transform: `translate3d(${pan.value.x}px, ${pan.value.y}px, 0)`
}))

const readFrame = () => {
  const el = frameEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  frame.value = { w: rect.width, h: rect.height }
}

const recenter = () => {
  pan.value = centeredPan(natural.value.w, natural.value.h, frame.value.w, frame.value.h, zoom.value)
}

const onLoad = () => {
  const el = imgEl.value
  natural.value = { w: el?.naturalWidth || 0, h: el?.naturalHeight || 0 }
  readFrame()
  recenter()
  ready.value = natural.value.w > 0 && natural.value.h > 0
}

const onError = () => {
  // 交不出图就别把用户困在裁剪界面里，退回上一层并说清楚
  toast('封面加载失败，无法调整构图', 'error')
  emit('cancel')
}

// 缩放以取景框中心为锚点：中心那块源图内容停在原地，画面不会「跳走」
const onZoomInput = (event) => {
  const next = Math.max(1, Math.min(COVER_CROP_MAX_ZOOM, Number(event.target.value) || 1))
  const prev = Math.max(1, zoom.value)
  if (next === prev || !natural.value.w || !frame.value.w) {
    zoom.value = next
    return
  }
  const s0 = baseScale.value * prev
  const s1 = baseScale.value * next
  const cx = (frame.value.w / 2 - pan.value.x) / s0
  const cy = (frame.value.h / 2 - pan.value.y) / s0
  zoom.value = next
  pan.value = clampPan(
    frame.value.w / 2 - cx * s1,
    frame.value.h / 2 - cy * s1,
    natural.value.w * s1,
    natural.value.h * s1,
    frame.value.w,
    frame.value.h
  )
}

let drag = null
const onDown = (event) => {
  if (locked.value || !ready.value) return
  drag = { id: event.pointerId, x: event.clientX, y: event.clientY, px: pan.value.x, py: pan.value.y }
  frameEl.value?.setPointerCapture?.(event.pointerId)
}
const onMove = (event) => {
  if (!drag || event.pointerId !== drag.id) return
  pan.value = clampPan(
    drag.px + (event.clientX - drag.x),
    drag.py + (event.clientY - drag.y),
    disp.value.w,
    disp.value.h,
    frame.value.w,
    frame.value.h
  )
}
const onUp = (event) => {
  if (!drag || event.pointerId !== drag.id) return
  drag = null
  try {
    frameEl.value?.releasePointerCapture?.(event.pointerId)
  } catch {
    // 指针已经释放过了，忽略
  }
}

const confirm = async () => {
  if (locked.value || !ready.value || !imgEl.value) return
  encoding.value = true
  try {
    // 直接拿页面上那个 <img> 当画布素材：用户看到的和裁出来的必然是同一张图。
    // （同源 /uploads 资源不会污染 canvas，所以 toBlob 不会抛 SecurityError）
    const region = cropRegion({
      srcW: natural.value.w,
      srcH: natural.value.h,
      frameW: frame.value.w,
      frameH: frame.value.h,
      zoom: zoom.value,
      panX: pan.value.x,
      panY: pan.value.y
    })
    const file = await cropToFile(imgEl.value, region, 'cover')
    emit('done', { file, width: Math.round(region.width), height: Math.round(region.height) })
  } catch {
    toast('裁剪失败，请重试', 'error')
  } finally {
    encoding.value = false
  }
}

let observer = null
onMounted(async () => {
  await nextTick()
  readFrame()
  if (typeof ResizeObserver !== 'undefined' && frameEl.value) {
    observer = new ResizeObserver(() => readFrame())
    observer.observe(frameEl.value)
  }
  // 缓存命中时 onLoad 可能已经错过（浏览器不会补发 load 事件）
  if (imgEl.value?.complete) onLoad()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

// 窗口尺寸变了 → 取景框像素尺寸变了 → 偏移量要重新夹一遍（区域本身与框大小无关）
watch(frame, () => {
  pan.value = clampPan(pan.value.x, pan.value.y, disp.value.w, disp.value.h, frame.value.w, frame.value.h)
})
</script>
