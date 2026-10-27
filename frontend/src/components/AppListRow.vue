<template>
  <!--
    Apple HIG 列表行（List Row）
    「inset grouped 列表」的一行：leading 图标 — 主标题/副标题 — trailing 值或 chevron。

    三种形态由 props 自动选择元素，调用方不用管：
      · to          → <router-link>（导航）
      · onClick     → <button>（动作）
      · 都没有      → <div>（纯展示）

    为什么行高分两档（44 / 60）：HIG 的最小可点区域是 44pt，单标题行刚好压线；
    带副标题的行需要两行文字，压到 44pt 会让行间距挤成一团，所以给 60pt。

    ⚠️ 分隔线由父级 .hig-list 画（> * + * 的 border-top），行本身不带线 ——
    否则最后一行会多出一条悬空的尾巴。
  -->
  <component
    :is="tag"
    v-bind="tagAttrs"
    class="hig-row"
    :class="[
      interactive ? 'hig-row-interactive' : '',
      dense ? 'min-h-11 py-2.5' : 'min-h-[60px]',
      danger ? '!text-clay' : ''
    ]"
    :data-test="testId"
    @click="onClick && onClick()"
  >
    <!-- leading：图标容器（HIG 圆角方块，29×29 是系统设置列表的尺寸） -->
    <span v-if="icon || $slots.leading" class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px]" :class="iconBgClass">
      <slot name="leading">
        <AppIcon :name="icon" class="h-4 w-4" />
      </slot>
    </span>

    <!-- 正文 -->
    <span class="min-w-0 flex-1">
      <slot>
        <span class="block truncate text-headline" :class="danger ? 'font-medium text-clay' : 'font-medium text-ink'">
          {{ title }}
        </span>
        <span v-if="subtitle" class="mt-0.5 block truncate text-footnote text-ink-mid">
          {{ subtitle }}
        </span>
      </slot>
    </span>

    <!-- trailing：值 / 自定义 / chevron -->
    <slot name="trailing">
      <span v-if="value !== null" class="shrink-0 text-footnote tabular-nums text-ink-dim">{{ value }}</span>
    </slot>
    <AppIcon v-if="chevron" name="chevronRight" class="h-4 w-4 shrink-0 text-ink-dim/60" />
  </component>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  // trailing 处的次要值；显式 null = 不渲染
  value: { type: [String, Number, null], default: null },
  icon: { type: String, default: '' },
  // leading 图标的底色，默认中性灰；传 'blue'/'red' 等切换语义色
  iconTone: { type: String, default: 'neutral' },
  chevron: { type: Boolean, default: false },
  // 有 to 或 onClick 即视为可交互（hover / active 反馈）
  to: { type: [String, Object], default: '' },
  onClick: { type: Function, default: null },
  // 破坏性行（退出登录 / 删除）：文字走 systemRed
  danger: { type: Boolean, default: false },
  // 单行紧凑模式（无副标题时用，行高 44）
  dense: { type: Boolean, default: false },
  testId: { type: String, default: '' }
})

const interactive = computed(() => !!props.to || !!props.onClick)

const tag = computed(() => {
  if (props.to) return 'router-link'
  if (props.onClick) return 'button'
  return 'div'
})

const tagAttrs = computed(() => {
  if (props.to) return { to: props.to }
  if (props.onClick) return { type: 'button' }
  return {}
})

// leading 图标底色：中性灰是 HIG 默认，语义色只在「这一行在说某件事」时用
const iconBgClass = computed(
  () =>
    ({
      neutral: 'bg-sand text-ink-mid',
      blue: 'bg-pine-soft text-pine-deep',
      red: 'bg-clay/10 text-clay',
      green: 'bg-green/10 text-green',
      orange: 'bg-amber-soft text-amber-warm'
    })[props.iconTone] || 'bg-sand text-ink-mid'
)
</script>
