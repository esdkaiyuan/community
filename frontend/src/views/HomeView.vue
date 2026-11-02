<template>
  <div>
    <!-- ============ Hero：手绘大标题 + 赛博星图 ============ -->
    <section v-if="!isFiltering" data-test="home-hero" class="relative overflow-hidden border-b border-line/70">
      <div class="cyber-grid cyber-grid-fade pointer-events-none absolute inset-0" aria-hidden="true"></div>
      <div class="site-shell relative grid gap-12 py-16 sm:py-20 lg:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)] lg:items-center lg:gap-16">
        <div class="animate-fade-up">
          <p class="eyebrow">ESDKAIYUAN · 共创社区</p>
          <h1 class="mt-6 font-brand text-[clamp(2.1rem,5vw,4.8rem)] font-bold leading-[1.08] tracking-[-0.02em] text-ink">
            让每一个想法，<br />
            <span class="marker-sketch text-ink-mid">遇见一起建造的人。</span>
          </h1>
          <p class="mt-7 text-callout font-semibold text-pine">致敬每一位共创者</p>
          <p class="mt-2 max-w-xl text-callout leading-relaxed text-ink-mid">
            把一个创意画成草图，找到愿意搭把手的人，一起把它做成。发布你的构想，或者加入别人的项目。
          </p>

          <!-- 创意 / 互助 / 合作：三步主题用手绘标签条说清平台在做什么 -->
          <div class="mt-6 flex flex-wrap items-center gap-2.5">
            <span class="sketch-tag text-subhead">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
                <circle cx="12" cy="10" r="4.4" />
                <path d="M10 16h4M10.8 19h2.4M12 2v1.6M5 6l1.2 1.2M19 6l-1.2 1.2M3 11h1.6M21 11h-1.6" />
              </svg>
              创意
            </span>
            <span class="sketch-tag text-subhead">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
                <circle cx="8" cy="8" r="2.6" />
                <circle cx="16" cy="8" r="2.6" />
                <path d="M3.5 19c0-3 2-4.6 4.5-4.6s4.5 1.6 4.5 4.6M11.5 19c0-3 2-4.6 4.5-4.6s4.5 1.6 4.5 4.6" />
              </svg>
              互助
            </span>
            <span class="sketch-tag text-subhead">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
                <path d="M3.5 11.5 12 4l8.5 7.5" />
                <path d="M6 10.5V20h12V10.5" />
                <rect x="10" y="14" width="4" height="6" stroke-width="1.5" />
              </svg>
              合作
            </span>
          </div>

          <div class="mt-8 flex flex-wrap items-center gap-3">
            <router-link to="/publish" class="btn-primary !px-6 !py-3">
              发布我的项目
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                <path d="M5 12h14m-6-6 6 6-6 6" />
              </svg>
            </router-link>
            <a href="#projects" class="btn-secondary !px-6 !py-3">浏览开源项目</a>
          </div>
          <div class="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-line/70 pt-6">
            <div>
              <p class="font-mono text-title2 font-semibold tracking-tight tabular-nums text-ink">{{ pad(total) }}</p>
              <p class="mt-1 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">共创项目</p>
            </div>
            <div>
              <p class="font-mono text-title2 font-semibold tracking-tight tabular-nums text-ink">{{ pad(categories.length) }}</p>
              <p class="mt-1 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">共创方向</p>
            </div>
            <div>
              <p class="font-mono text-title2 font-semibold tracking-tight text-ink">100%</p>
              <p class="mt-1 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">开放协作</p>
            </div>
          </div>
        </div>

        <div class="cosmic-panel aspect-[4/3]">
          <!-- 手绘星座连线：赛博感来自工程图纸，不是霓虹堆叠 -->
          <svg class="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 400 300" fill="none" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
            <path d="M40 220 120 170 175 205 250 130 330 165" stroke="#5BE0EB" stroke-width="1.2" stroke-linecap="round" opacity="0.55" />
            <path d="M120 170 95 110 160 70 250 130" stroke="#5BE0EB" stroke-width="1" stroke-linecap="round" opacity="0.32" />
            <path d="M30 60c30 6 46 14 62 32" stroke="#5BE0EB" stroke-width="1" stroke-dasharray="4 6" opacity="0.3" />
            <path d="M285 240c25-10 48-10 78 2" stroke="#5BE0EB" stroke-width="1" stroke-dasharray="5 7" opacity="0.28" />
            <circle cx="120" cy="170" r="3" fill="#5BE0EB" opacity="0.85" />
            <circle cx="250" cy="130" r="4" fill="#BFF5FA" opacity="0.9" />
            <circle cx="330" cy="165" r="2.5" fill="#BFF5FA" opacity="0.7" />
            <circle cx="95" cy="110" r="2" fill="#BEF264" opacity="0.7" />
            <text x="126" y="190" fill="#BFF5FA" font-size="8" font-family="monospace" opacity="0.7">A-01</text>
            <text x="256" y="152" fill="#BFF5FA" font-size="8" font-family="monospace" opacity="0.55">B-07</text>
          </svg>
          <div class="relative flex h-full flex-col justify-between p-5 sm:p-6">
            <div class="flex items-start justify-between gap-3">
              <span class="cosmic-chip">Star Map · 01</span>
              <span class="cosmic-chip">地球 · 你在这里</span>
            </div>
            <div>
              <p class="font-brand text-[22px] font-semibold text-white">一个创意，连起一群同路人</p>
              <p class="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-white/55">// one idea connects a co-creator</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 深色索引带：终端式数据条，数字用等宽字，承接主站的 CONTENT INDEX -->
    <section v-if="!isFiltering" class="relative overflow-hidden border-b border-white/10 bg-[#0B0D10] text-white">
      <div class="cyber-grid-light pointer-events-none absolute inset-0 opacity-40" aria-hidden="true"></div>
      <div class="site-shell relative grid grid-cols-2 lg:grid-cols-5">
        <div class="col-span-2 flex flex-col justify-center py-6 lg:col-span-1">
          <p class="font-mono text-[10px] font-medium uppercase tracking-[0.2em] text-[#BFF5FA]/55">Content Index</p>
          <p class="mt-2 font-mono text-caption2 uppercase tracking-[0.1em] text-white/55">// 持续更新 · 开放协作</p>
        </div>
        <div v-for="stat in indexStats" :key="stat.label" class="border-l border-[#5BE0EB]/15 px-5 py-6">
          <p class="font-mono text-title2 font-semibold tabular-nums">{{ stat.value }}</p>
          <p class="mt-1 font-mono text-caption2 uppercase tracking-[0.1em] text-[#BFF5FA]/55">{{ stat.label }}</p>
        </div>
      </div>
    </section>

    <!-- 共创方向：手绘卡片 + 终端编号 -->
    <section v-if="!isFiltering" class="site-shell py-16 sm:py-20">
      <div class="flex flex-col gap-6 border-b border-line/70 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p class="eyebrow">Blueprint 01</p>
          <h2 class="section-heading mt-3">共创方向</h2>
        </div>
        <p class="max-w-md text-footnote leading-relaxed text-ink-mid">
          围绕社区的真实需求，把技术能力转化为可以持续迭代的共创项目。
        </p>
      </div>
      <div class="mt-8 grid gap-4 md:grid-cols-3">
        <article
          v-for="(cat, i) in directionCards"
          :key="cat.id || cat.name"
          class="card group relative p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-pine/40 hover:shadow-card-hover"
        >
          <div class="flex items-start justify-between">
            <p class="font-mono text-caption2 font-semibold uppercase tracking-[0.16em] text-pine">/ {{ pad(i + 1) }}</p>
            <span class="font-mono text-caption1 text-ink-dim" aria-hidden="true">+</span>
          </div>
          <h3 class="mt-6 font-brand text-title2 font-semibold tracking-normal text-ink">{{ cat.name }}</h3>
          <p class="mt-2 text-footnote leading-relaxed text-ink-mid">{{ cat.description }}</p>
          <div class="mt-6 flex items-center justify-between border-t border-line/70 pt-4 font-mono text-caption2 uppercase tracking-[0.08em] text-ink-dim">
            <span>{{ cat.count || 0 }} 个项目</span>
            <span class="text-pine transition-transform group-hover:translate-x-0.5">Explore</span>
          </div>
        </article>
      </div>
    </section>

    <!-- ============ 项目广场 ============ -->
    <section id="projects" class="site-shell scroll-mt-20 py-16 sm:py-20">
      <div class="flex flex-col gap-6 border-b border-line/70 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p class="eyebrow">Projects 02</p>
          <h2 class="section-heading mt-3">{{ isFiltering ? '浏览项目' : '开源项目' }}</h2>
        </div>
        <p class="max-w-md text-footnote leading-relaxed text-ink-mid">
          从技术开发到公益创新，把真实问题做成可以一起建造的项目。
        </p>
      </div>

      <div class="mt-8">
      <!-- 人物筛选：从主页「查看全部」进来时必须先说清在看谁，
           否则页面长得跟普通广场一模一样，用户不知道自己被筛过了 -->
      <div
        v-if="personMode"
        data-test="person-banner"
        class="mb-6 flex flex-wrap items-center gap-3 rounded-xl2 border border-line bg-pine-soft/40 px-4 py-3"
      >
        <span class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine text-callout font-semibold text-white">
          <img v-if="person?.user?.avatar" :src="person.user.avatar" alt="" class="h-full w-full object-cover" />
          <template v-else>{{ personInitial }}</template>
        </span>
        <div class="min-w-0 flex-1">
          <h2 class="truncate text-title3 font-semibold text-ink" data-test="person-title">{{ personTitle }}</h2>
          <p class="mt-0.5 text-caption1 text-ink-dim" data-test="person-sub">{{ personSubtitle }}</p>
        </div>
        <router-link
          v-if="!personMissing"
          :to="`/user/${personId}`"
          class="btn-ghost !py-1 text-caption1"
          data-test="person-profile"
        >
          查看 TA 的主页
        </router-link>
        <button class="btn-ghost !py-1 text-caption1" data-test="clear-person" @click="clearPerson">
          清除筛选
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 搜索结果提示 -->
      <div v-if="query.search" class="mb-6 flex items-center gap-3">
        <h2 class="text-title3 font-semibold text-ink">「{{ query.search }}」的搜索结果</h2>
        <button class="btn-ghost !py-1 text-caption1" @click="clearSearch">
          清除搜索
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 标签筛选提示 -->
      <div v-if="query.tag" class="mb-6 flex flex-wrap items-center gap-3">
        <h2 class="flex items-center gap-2 text-title3 font-semibold text-ink">
          <AppIcon name="tag" class="h-4 w-4 text-ink-dim" />
          标签「{{ query.tag }}」下的项目
        </h2>
        <button class="btn-ghost !py-1 text-caption1" data-test="clear-tag" @click="clearTag">
          清除筛选
          <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 分类 -->
      <div class="flex flex-wrap items-center gap-2">
        <button class="cat-pill" :class="{ 'is-active': !query.categoryId }" @click="setCategory(null)">
          全部
        </button>
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="cat-pill"
          :class="{ 'is-active': query.categoryId === String(cat.id) }"
          @click="setCategory(cat.id)"
        >
          <AppIcon v-if="cat.icon" :name="categoryIcon(cat.icon)" class="h-3.5 w-3.5" />
          {{ cat.name }}
          <span class="text-caption1 opacity-60">{{ cat.count }}</span>
        </button>
      </div>

      <!-- 热门标签：分类之外的第二条浏览路径；没有标签数据时整行不渲染 -->
      <div v-if="popularTags.length" class="mt-3 flex flex-wrap items-center gap-2" data-test="popular-tags">
        <span class="inline-flex items-center gap-1 text-caption1 text-ink-dim">
          <AppIcon name="tag" class="h-3.5 w-3.5" />
          热门标签
        </span>
        <router-link
          v-for="t in popularTags"
          :key="t.name"
          :to="{ path: '/', query: { tag: t.name } }"
          class="chip-link"
          :class="query.tag === t.name ? '!bg-pine !text-white' : ''"
          :aria-current="query.tag === t.name ? 'page' : undefined"
        >
          # {{ t.name }}<span class="ml-1 tabular-nums opacity-60">{{ t.count }}</span>
        </router-link>
      </div>

      <!-- 筛选 / 排序
           排序是「多选一、选项平级」——正是 HIG 分段控件的语义，交给 AppSegmented；
           筛选是「可开可关的开关」，语义不同，保持 pill 形态——开关不该伪装成单选，
           否则用户会以为「编辑推荐」和「最新」互斥。 -->
      <div class="mt-6 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-for="f in FILTERS"
            :key="f.value"
            data-test="filter-chip"
            :data-value="f.value"
            class="inline-flex min-h-8 items-center gap-1.5 rounded-full px-3.5 text-footnote font-medium transition-colors"
            :class="query.filter === f.value ? 'bg-sand text-ink' : 'text-ink-mid hover:bg-sand/60'"
            :aria-pressed="query.filter === f.value"
            @click="toggleFilter(f.value)"
          >
            <AppIcon :name="f.icon" class="h-3.5 w-3.5" />
            {{ f.label }}
          </button>

          <!-- 只看收藏（登录后可用，跨分类的个人视图） -->
          <span v-if="userStore.isLoggedIn" class="mx-0.5 h-5 w-px shrink-0 bg-line" aria-hidden="true"></span>
          <button
            v-if="userStore.isLoggedIn"
            class="inline-flex min-h-8 items-center gap-1.5 rounded-full px-3.5 text-footnote font-medium transition-colors"
            :class="onlyFavorited ? 'bg-sand text-pine' : 'text-ink-mid hover:bg-sand/60'"
            :aria-pressed="onlyFavorited"
            @click="toggleFavorited"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" :fill="onlyFavorited ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 21 12 16.4 5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
            </svg>
            只看收藏
          </button>
        </div>

        <AppSegmented
          :model-value="query.sort"
          :options="SORTS"
          aria-label="排序方式"
          test-id="sort-chip"
          @update:model-value="setSort"
        />
      </div>

      <!-- 排序口径说明：只在「本周热门」下出现，否则用户看不出这个顺序是怎么来的 -->
      <p
        v-if="query.sort === 'trending'"
        data-test="trend-hint"
        class="mt-3 text-caption1 text-ink-dim"
      >
        按近 7 天的活跃度排序：参与 ×3、评论 ×2、点赞 ×1；卡片上的「本周 N」就是这项得分。
      </p>

      <!-- 加载中 -->
      <div v-if="loading" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <ProjectCardSkeleton v-for="i in 8" :key="i" />
      </div>

      <!-- 加载失败 -->
      <EmptyState
        v-else-if="loadError"
        icon="triangle-alert"
        title="加载失败了"
        description="可能是网络或服务暂时不可用，请稍后重试。"
      >
        <button class="btn-primary" @click="fetchProjects">重新加载</button>
      </EmptyState>

      <!-- 空结果：被筛选的人不存在（URL 里的编号是手改的或账号已注销） -->
      <EmptyState
        v-else-if="personMissing"
        icon="user"
        title="找不到这位共创者"
        description="Ta 可能已经注销，或者链接里的编号不对。"
      >
        <button class="btn-primary" @click="clearPerson">看看全部项目</button>
      </EmptyState>

      <!-- 空结果：人物筛选下的「TA 一个都还没有」，要带上名字而不是笼统的「这里还很安静」 -->
      <EmptyState
        v-else-if="!projects.length && personMode"
        :icon="personMode === 'creator' ? 'lightbulb' : 'users'"
        :title="emptyPersonTitle"
        :description="emptyPersonDesc"
      >
        <button class="btn-secondary" @click="clearPerson">看看全部项目</button>
      </EmptyState>

      <!-- 空结果：只看收藏 -->
      <EmptyState
        v-else-if="!projects.length && onlyFavorited"
        icon="bookmark"
        title="还没有收藏任何项目"
        description="在项目详情页点一下「收藏」，把心动的创意收进这里慢慢看。"
      >
        <button class="btn-primary" @click="toggleFavorited">去看看全部项目</button>
      </EmptyState>

      <!-- 空结果：标签筛选 -->
      <EmptyState
        v-else-if="!projects.length && query.tag"
        icon="tag"
        :title="`还没有「${query.tag}」标签的项目`"
        description="换个标签看看，或者发布一个打了该标签的项目。"
      >
        <button class="btn-secondary" @click="clearTag">看看全部项目</button>
        <router-link to="/publish" class="btn-primary">发布项目</router-link>
      </EmptyState>

      <!-- 空结果 -->
      <EmptyState
        v-else-if="!projects.length"
        icon="sprout"
        :title="query.search ? '没有找到相关项目' : '这里还很安静'"
        :description="query.search ? '换个关键词试试，或者浏览全部项目。' : '成为第一个发布项目的人，让创意在这里发芽。'"
      >
        <router-link to="/publish" class="btn-primary">发布第一个项目</router-link>
      </EmptyState>

      <!-- 项目网格 -->
      <template v-else>
        <div data-test="projects-grid" class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <ProjectCard
            v-for="(p, i) in projects"
            :key="p.id"
            v-reveal="Math.min(i, 7) * 60"
            :project="p"
            :trend="query.sort === 'trending' ? p.trendScore : null"
            @favorite-change="onFavoriteChange"
          />
        </div>

        <div class="mt-10">
          <Pagination :page="page" :total="total" :page-size="PAGE_SIZE" @change="setPage" />
        </div>
      </template>
      </div>
    </section>

    <!-- 参与方式：三种参与深度，承接主站的 Identity System -->
    <section v-if="!isFiltering" class="border-y border-line/70 bg-cream/60">
      <div class="site-shell py-16 sm:py-20">
        <div class="flex flex-col gap-6 border-b border-line/70 pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p class="eyebrow">Identity 03</p>
            <h2 class="section-heading mt-3">参与方式</h2>
          </div>
          <p class="max-w-md text-footnote leading-relaxed text-ink-mid">
            三种参与深度，总有一种适合你。无论只是路过，还是准备长期协作，这里都为你保留位置。
          </p>
        </div>
        <div class="mt-8 grid gap-4 md:grid-cols-3">
          <article v-for="(role, i) in ROLES" :key="role.title" class="card flex flex-col p-6">
            <div class="flex items-start justify-between gap-3">
              <p class="font-mono text-caption2 font-semibold uppercase tracking-[0.16em] text-pine">/ {{ pad(i + 1) }}</p>
              <span class="rounded-full border border-line bg-sand px-2.5 py-0.5 font-mono text-caption2 uppercase tracking-[0.06em] text-ink-dim">{{ role.subtitle }}</span>
            </div>
            <h3 class="mt-6 font-brand text-title2 font-semibold tracking-normal text-ink">{{ role.title }}</h3>
            <p class="mt-2 text-footnote leading-relaxed text-ink-mid">{{ role.desc }}</p>
            <ul class="mt-6 space-y-2.5 border-t border-line/70 pt-5 text-footnote text-ink-mid">
              <li v-for="item in role.items" :key="item" class="flex items-start gap-2">
                <AppIcon name="check" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-pine" />
                <span>{{ item }}</span>
              </li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <!-- 深色 CTA：手绘工程纸面板 -->
    <section v-if="!isFiltering" class="site-shell py-16 sm:py-20">
      <div class="sketch-panel relative overflow-hidden bg-[#0A0C10] px-6 py-12 text-white sm:px-12 sm:py-16">
        <div class="cyber-grid-light pointer-events-none absolute inset-0 opacity-35" aria-hidden="true"></div>
        <div class="pointer-events-none absolute -right-24 -top-28 h-72 w-72 rounded-full bg-pine/25 blur-3xl"></div>
        <div class="relative grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <p class="font-mono text-caption2 font-medium uppercase tracking-[0.18em] text-[#BFF5FA]/55">// Open Call</p>
            <h2 class="mt-4 font-brand text-[clamp(1.9rem,3.4vw,3.6rem)] font-bold leading-[1.12] tracking-[-0.01em]">
              把手上的想法，<br />交给一起建造的人。
            </h2>
          </div>
          <div class="lg:justify-self-end">
            <p class="max-w-sm text-footnote leading-relaxed text-white/60">
              无论你只是路过，还是准备长期参与，这里都为你保留位置。
            </p>
            <div class="mt-6 flex flex-wrap gap-3">
              <router-link to="/publish" class="btn-inverse">发布项目</router-link>
              <a href="#projects" class="btn-inverse-outline">浏览项目</a>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProjects, getProjectTags } from '@/api/project'
import { getCategories } from '@/api/category'
import { getPublicProfile } from '@/api/user'
import { categoryIcon } from '@/utils/categoryIcon'
import { useUserStore } from '@/store/user'
import AppIcon from '@/components/AppIcon.vue'
import ProjectCard from '@/components/ProjectCard.vue'
import ProjectCardSkeleton from '@/components/ProjectCardSkeleton.vue'
import EmptyState from '@/components/EmptyState.vue'
import Pagination from '@/components/Pagination.vue'
import AppSegmented from '@/components/AppSegmented.vue'

const PAGE_SIZE = 12
const pad = (value) => String(value ?? 0).padStart(2, '0')

// 「热门」已从筛选里去掉：它与排序里的「最热」是同一件事（都按互动量排），
// 而它依赖的 is_hot 标记位没有任何代码维护，点下去只能得到空列表。
const FILTERS = [{ label: '编辑推荐', value: 'recommend', icon: 'star' }]
const SORTS = [
  { label: '最新', value: 'latest' },
  { label: '最热', value: 'hot' },
  { label: '参与最多', value: 'participants' },
  { label: '本周热门', value: 'trending' }
]

// 分类接口异常时首页仍要成立：用种子里最稳定的三个方向兜底
const DIRECTION_FALLBACKS = [
  { name: '技术开发', description: '软件、应用、工具开发' },
  { name: '设计创意', description: 'UI/UX、视觉设计' },
  { name: '公益/社会创新', description: '社会公益项目' }
]

const ROLES = [
  {
    title: '浏览者',
    subtitle: 'Free Access',
    desc: '无需注册即可浏览社区里的公开内容，先看看大家在做什么。',
    items: ['浏览全部公开项目', '阅读评论与共创者主页', '收藏感兴趣的项目']
  },
  {
    title: '创作者',
    subtitle: 'Content Creation',
    desc: '注册后发布自己的项目，把想法写清楚，让同行者找到你。',
    items: ['发布项目与招募伙伴', '参与评论与讨论', '收到站内通知']
  },
  {
    title: '共创者',
    subtitle: 'Deep Participation',
    desc: '加入别人的项目，长期贡献技能与时间，把想法一起做出来。',
    items: ['加入项目并长期协作', '贡献技能与资源', '参与项目讨论与复盘']
  }
]

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const categories = ref([])
const popularTags = ref([])
const projects = ref([])
const total = ref(0)
const loading = ref(true)
const loadError = ref(false)

const directionCards = computed(() => {
  const list = categories.value.length ? categories.value.slice(0, 3) : DIRECTION_FALLBACKS
  return list.map((cat) => ({
    ...cat,
    description: cat.description || '把真实问题做成可以一起建造的项目。'
  }))
})

const indexStats = computed(() => [
  { value: pad(total.value), label: '共创项目' },
  { value: pad(categories.value.length), label: '共创方向' },
  { value: pad(popularTags.value.length), label: '热门标签' },
  { value: '100%', label: '开放协作' }
])

// 筛选状态完全由路由 query 驱动，可分享、可后退
const query = reactive({
  categoryId: route.query.categoryId || null,
  tag: route.query.tag || '',
  search: route.query.search || '',
  filter: route.query.filter || '',
  favorited: route.query.favorited || '',
  sort: route.query.sort || 'latest',
  // 这两个来自主页「查看全部」（creatorId=TA 发布的 / participantId=TA 参与的）
  creatorId: route.query.creatorId || null,
  participantId: route.query.participantId || null
})
const page = ref(Number(route.query.page) || 1)

// 被筛选的共创者信息；只拿公开资料用于上下文展示，不参与列表查询
const person = ref(null)
const personMissing = ref(false)
let personSeq = 0

const personMode = computed(() => (query.creatorId ? 'creator' : query.participantId ? 'participant' : null))
const personId = computed(() => query.creatorId || query.participantId || '')
const personName = computed(() => person.value?.user?.username || '这位共创者')
const personInitial = computed(() => personName.value.slice(0, 1).toUpperCase())
const personTitle = computed(() =>
  personMode.value === 'participant' ? `${personName.value} 参与的共创` : `${personName.value} 发布的项目`
)
const personSubtitle = computed(() => {
  if (personMissing.value) return '链接里的编号可能不对'
  if (personMode.value === 'participant') return `TA 作为伙伴加入的项目，不含 TA 自己发起的（共 ${total.value} 个）`
  return `共 ${total.value} 个项目`
})
const emptyPersonTitle = computed(() =>
  personMode.value === 'participant' ? `${personName.value} 还没有参与别人的项目` : `${personName.value} 还没有发布项目`
)
const emptyPersonDesc = computed(() =>
  personMode.value === 'participant'
    ? 'TA 目前只是自己项目的发起人。去 TA 的主页看看发布过什么。'
    : '想法攒够了就会开花，先去看看 TA 参与过的共创。'
)

// 「只看收藏」是登录用户的个人视图，未登录时即便 query 带着也不生效
const onlyFavorited = computed(() => query.favorited === '1' && userStore.isLoggedIn)

const isFiltering = computed(
  () =>
    !!(
      query.search ||
      query.tag ||
      query.categoryId ||
      query.filter ||
      onlyFavorited.value ||
      personMode.value ||
      (route.query.page && page.value > 1)
    )
)

const syncRoute = () => {
  const q = {}
  if (query.categoryId) q.categoryId = query.categoryId
  if (query.tag) q.tag = query.tag
  if (query.search) q.search = query.search
  if (query.filter) q.filter = query.filter
  if (query.creatorId) q.creatorId = query.creatorId
  if (query.participantId) q.participantId = query.participantId
  if (onlyFavorited.value) q.favorited = '1'
  if (query.sort !== 'latest') q.sort = query.sort
  if (page.value > 1) q.page = page.value
  router.push({ path: '/', query: q })
}

const setCategory = (id) => {
  query.categoryId = id ? String(id) : null
  page.value = 1
  syncRoute()
}
const toggleFilter = (f) => {
  query.filter = query.filter === f ? '' : f
  page.value = 1
  syncRoute()
}
const toggleFavorited = () => {
  query.favorited = onlyFavorited.value ? '' : '1'
  page.value = 1
  syncRoute()
}
const setSort = (s) => {
  query.sort = s
  page.value = 1
  syncRoute()
}
const setPage = (p) => {
  page.value = p
  syncRoute()
  document.getElementById('projects')?.scrollIntoView({ behavior: 'smooth' })
}
const clearSearch = () => {
  query.search = ''
  page.value = 1
  syncRoute()
}
const clearTag = () => {
  query.tag = ''
  page.value = 1
  syncRoute()
}
// 人物筛选与标签/搜索一样是「可清除」的临时视图，清掉后回到全量广场
const clearPerson = () => {
  query.creatorId = null
  query.participantId = null
  page.value = 1
  syncRoute()
}

// 拉被筛选者的公开资料只为在 banner 里报出名字；失败说明这人不存在（编号手改 / 已注销）
const loadPerson = async (id) => {
  if (!id) {
    person.value = null
    personMissing.value = false
    return
  }
  const seq = ++personSeq
  person.value = null
  personMissing.value = false
  try {
    const data = (await getPublicProfile(id)).data
    // 快速切人时旧请求可能后到，用序号丢弃过期响应
    if (seq !== personSeq) return
    person.value = data
  } catch {
    if (seq !== personSeq) return
    personMissing.value = true
  }
}

// 「只看收藏」视图里取消收藏即移出列表，并把总数同步减一
const onFavoriteChange = ({ id, favorited }) => {
  if (!onlyFavorited.value || favorited) return
  projects.value = projects.value.filter((p) => p.id !== id)
  if (total.value > 0) total.value -= 1
}

const fetchProjects = async () => {
  loading.value = true
  loadError.value = false
  try {
    const res = await getProjects({
      page: page.value,
      pageSize: PAGE_SIZE,
      categoryId: query.categoryId || undefined,
      tag: query.tag || undefined,
      search: query.search || undefined,
      filter: query.filter || undefined,
      favorited: onlyFavorited.value ? '1' : undefined,
      creatorId: query.creatorId || undefined,
      participantId: query.participantId || undefined,
      sort: query.sort
    })
    projects.value = res.data.projects
    total.value = res.data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

const fetchCategories = async () => {
  try {
    const res = await getCategories()
    categories.value = res.data
  } catch {
    // 分类加载失败不阻塞页面
  }
}

// 热门标签失败也不阻塞：没有标签数据时这一行自然不渲染
const fetchPopularTags = async () => {
  try {
    const res = await getProjectTags()
    popularTags.value = res.data || []
  } catch {
    popularTags.value = []
  }
}

// 外部路由变化（如导航栏搜索、页脚快捷链接）时同步并重新拉取
watch(
  () => route.query,
  (q) => {
    if (route.path !== '/') return
    query.categoryId = q.categoryId || null
    query.tag = q.tag || ''
    query.search = q.search || ''
    query.filter = q.filter || ''
    query.favorited = q.favorited || ''
    query.sort = q.sort || 'latest'
    query.creatorId = q.creatorId || null
    query.participantId = q.participantId || null
    page.value = Number(q.page) || 1
    loadPerson(query.creatorId || query.participantId)
    fetchProjects()
  }
)

// 登出后「只看收藏」失效，需要清掉筛选并回到全量列表
watch(
  () => userStore.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn && query.favorited) {
      query.favorited = ''
      page.value = 1
      syncRoute()
    }
  }
)

onMounted(() => {
  fetchCategories()
  fetchPopularTags()
  loadPerson(personId.value)
  fetchProjects()
})
</script>

