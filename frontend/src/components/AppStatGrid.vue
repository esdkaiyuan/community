<template>
  <!--
    Apple HIG 规格条（Spec Grid）
    一组同级的数字指标：参与数 / 点赞数 / 浏览数…

    视觉取自 apple.com 参数表：格子之间留 1px 间隙、露出底色当分隔线
    （比给每个格子描边更细，且不会在相邻处叠成 2px 的粗线）。
    数字用 tabular-nums —— 等宽数字，翻页时数字跳动不会带着布局一起抖。

    data-test：整条用 testId；单格优先取 item.test（存量脚本按 detail-views /
    detail-created 定位具体格子，名字必须落得住），没给才退回 `${testId}-${index}`。
  -->
  <div
    class="hig-stat-grid"
    :class="colsClass"
    :data-test="testId"
  >
    <div
      v-for="(item, i) in items"
      :key="item.label"
      class="hig-stat-cell"
      :data-test="item.test || (testId ? `${testId}-${i}` : undefined)"
    >
      <p class="text-title2 font-semibold tabular-nums text-ink">{{ item.value }}</p>
      <p class="mt-0.5 text-caption1 text-ink-mid">{{ item.label }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // [{ label, value }]
  items: { type: Array, required: true },
  // 列数：2 / 3 / 4；auto = 按项数自动分（≤4 用项数，否则 2 列起）
  cols: { type: [Number, String], default: 'auto' },
  testId: { type: String, default: '' }
})

// 断点递进：窄屏 2 列起步，sm 起按配置展开 —— 4 列在 375px 上会挤成两行窄条
const colsClass = computed(() => {
  const n = props.cols === 'auto' ? Math.min(props.items.length, 4) : Number(props.cols)
  return {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-4'
  }[n] || 'grid-cols-2'
})
</script>
