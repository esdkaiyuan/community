<template>
  <!--
    Apple HIG 分段控件（Segmented Control）
    用于「二选一到多选一」且选项平级、数量少（2~5）的切换：排序、筛选、视图切换。

    为什么不是一排 pill：pill 没有容器，选中态只能靠背景色变化表达，
    在深色下几乎看不出「哪一片是按下去的」。分段控件的语言是「滑块在轨道里移动」，
    选中段有独立白底 + 极淡描边，未选中段是轨道本身——层级清楚，深浅色都成立。

    可访问性刻意用「按钮 + aria-pressed」而不是 role="tablist"/"tab"：
    分段控件在语义上确实是切换按钮组，而 role="tab" 会把它从 button 角色里摘出去，
    读屏与自动化（get_by_role("button", name=…)）都按 tab 去理解，
    等于为了一个视觉形态牺牲了它本来的身份。aria-pressed 才是这种控件的正解。
  -->
  <div
    class="hig-segmented"
    role="group"
    :aria-label="ariaLabel"
    :data-test="testId ? `${testId}-group` : undefined"
  >
    <button
      v-for="opt in options"
      :key="opt.value"
      type="button"
      class="hig-segmented-item"
      :class="[
        opt.value === modelValue ? 'is-active' : '',
        iconOnly ? 'is-icon' : ''
      ]"
      :aria-pressed="opt.value === modelValue"
      :data-test="opt.test || testId || undefined"
      :data-value="opt.value"
      :title="opt.label"
      @click="emit('update:modelValue', opt.value)"
    >
      <AppIcon v-if="opt.icon" :name="opt.icon" class="h-3.5 w-3.5" />
      <span v-if="!iconOnly">{{ opt.label }}</span>
      <span v-else class="sr-only">{{ opt.label }}</span>
    </button>
  </div>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  // 当前选中项的 value
  modelValue: { type: [String, Number], default: '' },
  // [{ label, value, icon? }]
  options: { type: Array, required: true },
  ariaLabel: { type: String, default: '切换视图' },
  // 只显示图标（窄屏节省横向空间）；标签仍以 sr-only 保留给读屏
  iconOnly: { type: Boolean, default: false },
  testId: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])
</script>
