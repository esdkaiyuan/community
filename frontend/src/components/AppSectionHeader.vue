<template>
  <!--
    Apple HIG 分区标题（Section Header）
    页面里每个「一块内容」的题头：标题 + 可选计数 + 右侧操作。

    抽出来的直接原因：ProfileView 里「我发布的项目 / 我的收藏 / 我参与的讨论」
    三个标题把同一段装饰（h-4 w-1 的竖条 + text-title3 + 计数）抄了三遍，
    改动一次要改三处，三处迟早漂移。

    HIG 的做法比竖条更克制：分区标题靠**字号与字重**区分层级，
    不加彩色装饰块——竖条在列表里会跟内容抢注意力，而标题的职责是分组说明。
  -->
  <div class="mb-4 flex items-end justify-between gap-3">
    <div class="flex min-w-0 items-baseline gap-2">
      <AppIcon v-if="icon" :name="icon" class="h-4 w-4 shrink-0 self-center text-ink-dim" />
      <!-- 计数必须留在 <h2> **内部**：「我的收藏（2）」是完整的一个标题，
           拆到标题外等于把附属信息从标题语义里摘出去 —— 读屏读不到，
           get_by_role("heading") 也取不到（verify_favorites 就是这么断言的，
           拆出去后 "（2）" 不在 inner_text 里，断言直接变红）。
           countTestId：存量脚本按 created-count / joined-count 直接取计数。 -->
      <h2 class="truncate text-title3 font-semibold text-ink">
        {{ title }}<span
          v-if="count !== null"
          :data-test="countTestId || undefined"
          class="ml-1 text-footnote font-normal tabular-nums text-ink-dim"
        >（{{ count }}）</span>
      </h2>
    </div>

    <!-- 右侧操作（查看全部 / 发布新项目…） -->
    <div v-if="$slots.action" class="flex shrink-0 items-center gap-1">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'

defineProps({
  title: { type: String, required: true },
  // 显式传 null 表示「暂无计数」（如还在加载中），不渲染括号
  count: { type: [Number, String, null], default: null },
  // 计数元素的 data-test 锚点（供端到端脚本取数）
  countTestId: { type: String, default: '' },
  icon: { type: String, default: '' }
})
</script>
