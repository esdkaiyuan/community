<template>
  <!-- 发布 / 编辑共用「项目工作台」：左侧分段表单，右侧实时预览 -->
  <form class="publish-window" data-test="project-form" @submit.prevent="handleSubmit">
    <!-- 窗口标题栏 -->
    <header class="publish-window__bar">
      <div class="flex min-w-0 items-center gap-3">
        <span class="window-dots" aria-hidden="true">
          <i class="window-dot window-dot--pine"></i>
          <i class="window-dot window-dot--amber"></i>
          <i class="window-dot window-dot--clay"></i>
        </span>
        <div class="min-w-0">
          <p class="font-mono text-caption2 uppercase tracking-[0.16em] text-ink-dim">
            {{ isEdit ? 'PROJECT / EDIT' : 'PROJECT / NEW' }}
          </p>
          <h1 class="mt-0.5 truncate font-brand text-title2 font-bold text-ink">
            {{ isEdit ? '编辑项目' : '发布新项目' }}
          </h1>
        </div>
      </div>

      <div class="flex shrink-0 items-center gap-2">
        <span class="hidden text-caption1 text-ink-dim sm:inline">
          {{ isEdit ? '修改即时生效' : '发布后仍可编辑' }}
        </span>
        <button
          type="button"
          class="window-close"
          aria-label="关闭窗口"
          @click="handleCancel"
        >
          <AppIcon name="x" class="h-4 w-4" />
        </button>
      </div>
    </header>

    <div class="grid lg:grid-cols-[minmax(0,1fr)_340px]">
      <!-- ============ 表单主体 ============ -->
      <main class="min-w-0 p-5 sm:p-7 lg:p-8">
        <!-- 移动端准备度 -->
        <div class="mb-6 flex items-center gap-3 rounded-12 border border-line bg-sand/40 px-4 py-3 lg:hidden">
          <span class="shrink-0 font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">准备度 {{ progress }}%</span>
          <div class="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
            <div class="h-full rounded-full bg-pine transition-all duration-300" :style="{ width: `${progress}%` }"></div>
          </div>
          <span class="shrink-0 font-mono text-caption2 tabular-nums text-ink-dim">{{ completedCount }}/{{ completion.length }}</span>
        </div>

        <!-- 01 基本信息 -->
        <section class="form-section">
          <div class="form-section__head">
            <span class="step-index">01</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h2 class="text-headline font-semibold text-ink">基本信息</h2>
                <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">REQUIRED</span>
              </div>
              <p class="mt-1 text-caption1 leading-relaxed text-ink-dim">标题与分类决定项目在广场里的第一印象。</p>
            </div>
          </div>

          <div class="mt-5 space-y-5">
            <div>
              <label class="form-label" for="title">
                项目标题 <span class="text-clay">*</span>
              </label>
              <div class="relative">
                <input
                  id="title"
                  data-test="form-title"
                  v-model.trim="form.title"
                  type="text"
                  class="input title-input pr-16"
                  placeholder="一句话说清你的项目，例如：社区旧物改造工作坊"
                  maxlength="60"
                />
                <span class="input-counter">{{ form.title.length }}/60</span>
              </div>
              <p v-if="errors.title" class="form-error !mt-1.5">{{ errors.title }}</p>
            </div>

            <div>
              <label class="form-label">
                项目分类 <span class="text-clay">*</span>
              </label>
              <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                <button
                  v-for="cat in categories"
                  :key="cat.id"
                  type="button"
                  class="category-option"
                  :class="{ 'is-active': form.categoryId === cat.id }"
                  data-test="category-option"
                  :aria-pressed="form.categoryId === cat.id"
                  @click="form.categoryId = cat.id"
                >
                  <span class="category-option__icon">
                    <AppIcon v-if="cat.icon" :name="categoryIcon(cat.icon)" class="h-4 w-4" />
                    <AppIcon v-else name="sprout" class="h-4 w-4" />
                  </span>
                  <span class="min-w-0 truncate text-footnote font-medium">{{ cat.name }}</span>
                  <AppIcon v-if="form.categoryId === cat.id" name="check" class="ml-auto h-4 w-4 shrink-0" />
                </button>
              </div>
              <p v-if="errors.categoryId" class="form-error" data-test="error-category">{{ errors.categoryId }}</p>
              <p v-else class="mt-2 text-caption1 leading-relaxed text-ink-dim">分类决定项目出现在广场的哪一栏，选最贴近的一个即可。</p>
            </div>
          </div>
        </section>

        <!-- 02 项目故事 -->
        <section class="form-section">
          <div class="form-section__head">
            <span class="step-index">02</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h2 class="text-headline font-semibold text-ink">项目故事</h2>
                <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">REQUIRED</span>
              </div>
              <p class="mt-1 text-caption1 leading-relaxed text-ink-dim">写清「想做什么、为什么、需要谁」，比堆形容词更有吸引力。</p>
            </div>
          </div>

          <div class="mt-5">
            <label class="form-label" for="description">
              项目介绍 <span class="text-clay">*</span>
            </label>
            <textarea
              id="description"
              data-test="form-description"
              v-model.trim="form.description"
              class="input min-h-[220px] resize-y leading-[1.9]"
              placeholder="介绍一下：你想做什么？为什么想做？目前进展如何？需要什么样的伙伴？"
              maxlength="2000"
            ></textarea>
            <div class="mt-1.5 flex items-center justify-between gap-3">
              <p v-if="errors.description" class="form-error !mt-0">{{ errors.description }}</p>
              <p v-else class="text-caption1 text-ink-dim">首段会作为详情页头图的导语。</p>
              <span class="ml-auto shrink-0 font-mono text-caption1 tabular-nums text-ink-dim">{{ form.description.length }}/2000</span>
            </div>
          </div>
        </section>

        <!-- 03 协作信息 -->
        <section class="form-section">
          <div class="form-section__head">
            <span class="step-index">03</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h2 class="text-headline font-semibold text-ink">协作信息</h2>
                <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">OPTIONAL</span>
              </div>
              <p class="mt-1 text-caption1 leading-relaxed text-ink-dim">仓库与截止日期都是可选项，但能让伙伴更快判断要不要加入。</p>
            </div>
          </div>

          <div class="mt-5 space-y-5">
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="form-label" for="repositoryUrl">仓库地址</label>
                <input
                  id="repositoryUrl"
                  v-model.trim="form.repositoryUrl"
                  type="url"
                  inputmode="url"
                  class="input"
                  placeholder="https://github.com/…"
                  maxlength="255"
                  data-test="form-repo"
                />
                <p v-if="errors.repositoryUrl" class="form-error" data-test="error-repo">{{ errors.repositoryUrl }}</p>
                <p v-else class="mt-1.5 text-caption1 leading-relaxed text-ink-dim">详情页会展示「查看仓库」入口。</p>
              </div>

              <div>
                <label class="form-label" for="endDate">截止日期</label>
                <input
                  id="endDate"
                  v-model.trim="form.endDate"
                  type="date"
                  class="input"
                  data-test="form-end-date"
                />
                <p v-if="errors.endDate" class="form-error" data-test="error-end-date">{{ errors.endDate }}</p>
                <p v-else class="mt-1.5 text-caption1 leading-relaxed text-ink-dim">过了这天会标「已截止」，留空表示不设截止。</p>
              </div>
            </div>

            <div>
              <label class="form-label" for="tag">
                标签 <span class="text-caption1 font-normal text-ink-dim">（单个最多 {{ TAG_MAX_LENGTH }} 字、最多 {{ TAG_MAX_COUNT }} 个，回车添加）</span>
              </label>
              <div class="tag-field">
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
                  class="min-w-[8rem] flex-1 bg-transparent py-1 text-footnote outline-none placeholder:text-ink-dim"
                  :placeholder="form.tags.length ? '' : '例如：环保、开源、线下活动'"
                  :maxlength="TAG_MAX_LENGTH"
                  :disabled="form.tags.length >= TAG_MAX_COUNT"
                  @keydown.enter.prevent="addTagFromInput"
                  @keydown.backspace="onTagBackspace"
                />
              </div>

              <div v-if="showSuggestions" class="mt-3">
                <p class="mb-1.5 font-mono text-caption2 uppercase tracking-[0.1em] text-ink-dim">RECOMMENDED TAGS</p>
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
              <p v-else class="mt-2 text-caption1 leading-relaxed text-ink-dim">
                标签会进入广场的「热门标签」，是别人发现你这个项目的主要入口。
              </p>
            </div>
          </div>
        </section>

        <!-- 04 访问加密 -->
        <section class="form-section">
          <div class="form-section__head">
            <span class="step-index">04</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h2 class="text-headline font-semibold text-ink">访问加密</h2>
                <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">OPTIONAL</span>
              </div>
              <p class="mt-1 text-caption1 leading-relaxed text-ink-dim">
                可以只加密仓库地址，也可以把整份项目档案锁起来。每个账号最多只能创建 1 个加密项目。
              </p>
            </div>
          </div>

          <div class="mt-5 space-y-4">
            <div class="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <button
                v-for="option in LOCK_OPTIONS"
                :key="option.value"
                type="button"
                class="lock-option"
                :class="{ 'is-active': form.lockLevel === option.value, 'is-disabled': option.value !== 'none' && !canChooseEncryption }"
                :disabled="option.value !== 'none' && !canChooseEncryption"
                :aria-pressed="form.lockLevel === option.value"
                data-test="lock-option"
                @click="selectLockLevel(option.value)"
              >
                <span class="lock-option__icon">
                  <AppIcon :name="option.icon" class="h-4 w-4" />
                </span>
                <span class="min-w-0 text-left">
                  <span class="block text-footnote font-semibold">{{ option.title }}</span>
                  <span class="mt-0.5 block text-caption1 font-normal leading-relaxed text-ink-dim">{{ option.desc }}</span>
                </span>
                <AppIcon v-if="form.lockLevel === option.value" name="check" class="ml-auto h-4 w-4 shrink-0" />
              </button>
            </div>

            <div
              v-if="encryptedElsewhere"
              class="flex items-start gap-2.5 rounded-12 border border-[color:var(--c-amber-warm)]/30 bg-[color:var(--c-amber-warm)]/10 px-3.5 py-3"
              data-test="lock-quota-hint"
            >
              <AppIcon name="info" class="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--c-amber-warm)]" />
              <p class="text-caption1 leading-relaxed text-ink-mid">
                你已有一个加密项目「{{ encryptedElsewhere.title }}」，每个账号最多 1 个。
                当前项目只能保持公开；如需调整加密设置，请先
                <router-link :to="`/project/${encryptedElsewhere.id}/edit`" class="font-medium text-pine underline-offset-4 hover:underline">
                  编辑那个项目
                </router-link>
                。
              </p>
            </div>

            <div v-if="form.lockLevel !== 'none'" class="lock-password-box">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <label class="form-label !mb-0" :for="lockPasswordId">
                  访问密码 <span class="text-clay">*</span>
                </label>
                <span class="font-mono text-caption2 uppercase tracking-[0.1em] text-ink-dim">
                  {{ needsNewLockPassword ? 'SET PASSWORD' : 'KEEP / CHANGE' }}
                </span>
              </div>
              <input
                :id="lockPasswordId"
                v-model="form.lockPassword"
                type="password"
                class="input mt-2"
                :placeholder="needsNewLockPassword ? '至少 6 位，只有知道密码的人才能查看' : '留空则沿用当前密码'"
                maxlength="64"
                autocomplete="new-password"
                data-test="lock-password"
              />
              <p v-if="errors.lockPassword" class="form-error" data-test="error-lock-password">{{ errors.lockPassword }}</p>
              <p v-else class="mt-1.5 text-caption1 leading-relaxed text-ink-dim">
                {{
                  form.lockLevel === 'repo'
                    ? '项目内容保持公开，只有「查看仓库」需要输入这串密码。'
                    : '项目介绍、标签、仓库地址与共创伙伴都会隐藏，输入密码后才能查看。'
                }}
                密码只保存加密后的哈希，之后可以随时在这里修改。
              </p>
            </div>
          </div>
        </section>

        <!-- 05 封面 -->
        <section class="form-section">
          <div class="form-section__head">
            <span class="step-index">05</span>
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h2 class="text-headline font-semibold text-ink">封面</h2>
                <span class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">OPTIONAL</span>
              </div>
              <p class="mt-1 text-caption1 leading-relaxed text-ink-dim">封面统一按 16:9 展示。拖动裁剪后，框内留下的画面就是广场卡片上的最终封面。</p>
            </div>
          </div>

          <div class="mt-5">
            <!-- 调整构图：取景框接管预览区 -->
            <CoverCropper
              v-if="cropping"
              :src="cropSource"
              :busy="uploading"
              @done="applyCrop"
              @cancel="cropping = false"
            />

            <div v-else-if="form.coverImage" class="group" data-test="cover-preview">
              <div class="relative overflow-hidden rounded-14 border border-line">
                <img
                  :src="form.coverImage"
                  alt="封面预览"
                  class="aspect-[16/9] w-full object-cover"
                  @error="coverBroken = true"
                  @load="coverBroken = false"
                />

                <!-- 比例标记：告诉用户这里就是卡片封面，不是别的预览 -->
                <span class="cover-card-mark pointer-events-none">CARD / 16:9</span>

                <div
                  v-if="uploading"
                  class="absolute inset-0 flex items-center justify-center gap-2 bg-black/55 text-white"
                  data-test="cover-uploading"
                >
                  <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
                    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
                  </svg>
                  <span class="text-footnote">上传中…</span>
                </div>

                <div v-else class="absolute right-3 top-3 flex gap-2">
                  <button
                    type="button"
                    class="cover-action"
                    data-test="cover-replace"
                    @click="pickFile"
                  >
                    更换
                  </button>
                  <button
                    type="button"
                    class="cover-action cover-action--danger"
                    data-test="cover-remove"
                    @click="removeCover"
                  >
                    移除
                  </button>
                </div>
              </div>

              <button
                v-if="!uploading && canCrop"
                type="button"
                class="cover-crop-bar"
                data-test="cover-crop-open"
                @click="cropping = true"
              >
                <span class="cover-crop-bar__icon"><AppIcon name="crop" class="h-4 w-4" /></span>
                <span class="min-w-0 flex-1 text-left">
                  <span class="block font-medium text-ink">拖动裁剪 · 卡片 16:9</span>
                  <span class="mt-0.5 block text-caption1 text-ink-dim">框内 = 广场卡片实际展示的封面，按住图片拖动即可调整</span>
                </span>
                <span class="shrink-0 font-mono text-caption2 uppercase tracking-[0.12em] text-pine">调整 →</span>
              </button>
              <p v-else-if="!uploading && !canCrop" class="mt-2 text-caption1 leading-relaxed text-ink-dim">
                外链与 GIF 无法在浏览器内重新裁剪，卡片会居中裁切展示。
              </p>
            </div>

            <button
              v-else
              type="button"
              class="upload-drop cover-drop"
              :class="{ 'is-dragging': dragging }"
              data-test="cover-drop"
              @click="pickFile"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="onDrop"
            >
              <span class="cover-drop__icon"><AppIcon name="image" class="h-5 w-5" /></span>
              <span class="font-medium">点击选择图片，或拖到这里</span>
              <span class="text-caption1 text-ink-dim">支持 JPG / PNG / WebP / GIF，大图会先自动压缩再上传</span>
            </button>

            <input
              ref="fileInput"
              type="file"
              class="hidden"
              accept="image/jpeg,image/png,image/webp,image/gif"
              data-test="cover-input"
              @change="onFileChange"
            />

            <p v-if="coverBroken && form.coverImage && !uploading" class="form-error" data-test="cover-broken">
              图片无法加载，保存后将显示默认封面
            </p>
            <p v-else-if="!form.coverImage" class="mt-2 text-caption1 text-ink-dim">
              不填也没关系，我们会按项目生成一个漂亮的默认封面。
            </p>

            <button
              type="button"
              class="mt-2 text-caption1 text-ink-dim transition-colors hover:text-ink"
              data-test="cover-toggle-url"
              @click="showUrlInput = !showUrlInput"
            >
              {{ showUrlInput ? '收起链接输入' : '或粘贴一个图片链接' }}
            </button>
            <input
              v-if="showUrlInput"
              id="cover"
              v-model.trim="form.coverImage"
              type="url"
              class="input mt-2"
              placeholder="https://example.com/cover.jpg"
              data-test="cover-url"
            />
          </div>
        </section>
      </main>

      <!-- ============ 实时预览（桌面） ============ -->
      <aside class="preview-rail hidden lg:block">
        <div class="sticky top-20 space-y-4 py-8 pr-6">
          <div class="flex items-center justify-between">
            <p class="mono-label">LIVE PREVIEW</p>
            <span class="font-mono text-caption2 uppercase tracking-[0.1em] text-ink-dim">CARD</span>
          </div>

          <div class="preview-card">
            <div class="relative aspect-[16/9] overflow-hidden">
              <img
                v-if="form.coverImage && !coverBroken"
                :src="form.coverImage"
                alt=""
                class="h-full w-full object-cover"
              />
              <div
                v-else
                class="flex h-full w-full items-center justify-center"
                :style="{ background: previewPlaceholder.bg }"
              >
                <span class="select-none font-display text-5xl font-bold opacity-90" :style="{ color: previewPlaceholder.fg }">
                  {{ previewTitle.slice(0, 1) || '创' }}
                </span>
              </div>
              <span class="preview-category">{{ selectedCategory?.name || '未选择分类' }}</span>
            </div>

            <div class="p-4">
              <h3 class="line-clamp-2 font-brand text-title3 font-semibold leading-snug text-ink">{{ previewTitle }}</h3>
              <p class="mt-1.5 line-clamp-3 text-footnote leading-relaxed text-ink-mid">{{ previewDescription }}</p>

              <div v-if="form.tags.length" class="mt-3 flex flex-wrap gap-1.5">
                <span v-for="tag in form.tags.slice(0, 3)" :key="tag" class="chip-link"># {{ tag }}</span>
              </div>

              <div class="mt-4 flex items-center justify-between border-t border-line pt-3">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="flex h-6 w-6 shrink-0 items-center justify-center overflow-hidden rounded-full bg-pine-soft text-caption2 font-bold text-pine-deep">
                    <img v-if="userStore.avatar" :src="userStore.avatar" alt="" class="h-full w-full object-cover" />
                    <template v-else>{{ (userStore.username || '我').slice(0, 1).toUpperCase() }}</template>
                  </span>
                  <span class="truncate text-caption1 text-ink-mid">{{ userStore.username || '我' }}</span>
                  <span class="shrink-0 text-caption2 text-ink-dim">· 刚刚</span>
                </div>
                <span class="flex shrink-0 items-center gap-2 font-mono text-caption2 tabular-nums text-ink-dim">
                  <span class="flex items-center gap-0.5"><AppIcon name="heart" class="h-3 w-3" />0</span>
                  <span class="flex items-center gap-0.5"><AppIcon name="users" class="h-3 w-3" />0</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 准备度清单 -->
          <div class="progress-card">
            <div class="flex items-center justify-between">
              <p class="font-mono text-caption2 uppercase tracking-[0.12em] text-ink-dim">CHECKLIST</p>
              <span class="font-mono text-caption1 tabular-nums text-ink">{{ completedCount }}/{{ completion.length }}</span>
            </div>
            <div class="mt-2.5 h-1.5 overflow-hidden rounded-full bg-line">
              <div class="h-full rounded-full bg-pine transition-all duration-300" :style="{ width: `${progress}%` }"></div>
            </div>
            <ul class="mt-3 space-y-1.5">
              <li
                v-for="item in completion"
                :key="item.label"
                class="flex items-center gap-2 text-caption1"
                :class="item.done ? 'text-ink-mid' : 'text-ink-dim'"
              >
                <span
                  class="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border"
                  :class="item.done ? 'border-pine bg-pine text-white' : 'border-ink-dim/40'"
                >
                  <AppIcon v-if="item.done" name="check" class="h-2.5 w-2.5" />
                </span>
                <span>{{ item.label }}</span>
                <span v-if="!item.done" class="ml-auto font-mono text-caption2 text-ink-dim/70">{{ item.hint }}</span>
              </li>
            </ul>
          </div>

          <p class="text-caption1 leading-relaxed text-ink-dim">
            预览只模拟广场卡片。发布后你仍可随时回到这里修改标题、介绍与封面。
          </p>
        </div>
      </aside>
    </div>

    <!-- 窗口底栏 -->
    <footer class="publish-window__footer">
      <p class="hidden text-caption1 leading-relaxed text-ink-dim sm:block">
        {{ isEdit ? '保存后立即更新详情页。' : '发布后项目会出现在广场，并可随时编辑。' }}
      </p>
      <div class="ml-auto flex w-full items-center gap-2 sm:w-auto">
        <button type="button" class="btn-ghost flex-1 sm:flex-none !px-4" @click="handleCancel">
          {{ isEdit ? '放弃修改' : '取消' }}
        </button>
        <button
          type="submit"
          class="btn-primary flex-1 sm:flex-none !px-7 !py-2.5"
          :disabled="submitting || uploading"
          data-test="submit-project"
        >
          <svg v-if="submitting" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" class="opacity-25" />
            <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
          </svg>
          <AppIcon v-else :name="isEdit ? 'pencil' : 'sprout'" class="h-4 w-4" />
          {{ submitText }}
        </button>
      </div>
    </footer>
  </form>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createProject, updateProject, getProjectTags, getEncryptionStatus } from '@/api/project'
import { uploadCover, COVER_ACCEPT, COVER_MAX_BYTES } from '@/api/upload'
import { getCategories } from '@/api/category'
import { useUserStore } from '@/store/user'
import { categoryIcon } from '@/utils/categoryIcon'
import { stripEmoji } from '@/utils/text'
import { coverPalette } from '@/utils/placeholder'
import { TAG_MAX_COUNT, TAG_MAX_LENGTH, DEFAULT_TAG_SUGGESTIONS, addTagToList, cleanTag, toTagList } from '@/utils/tags'
import { compressImage, formatBytes } from '@/utils/imageCompress'
import { COVER_ASPECT_LABEL } from '@/utils/imageCrop'
import AppIcon from '@/components/AppIcon.vue'
import CoverCropper from '@/components/CoverCropper.vue'
import { toast } from '@/composables/useToast'

const props = defineProps({
  mode: { type: String, default: 'create' }, // create | edit
  project: { type: Object, default: null } // edit 模式下用于回填
})

const emit = defineEmits(['submitted'])

const router = useRouter()
const userStore = useUserStore()
const isEdit = computed(() => props.mode === 'edit')

const categories = ref([])
const popularTags = ref([])
const form = reactive({
  title: props.project?.title || '',
  description: props.project?.description || '',
  categoryId: props.project?.categoryId ?? null,
  tags: toTagList(props.project?.tags),
  coverImage: props.project?.coverImage || '',
  // 仓库地址 / 截止日期：接自 2026-10-03（这两列线上一直有数据但模型没声明，
  // 此前接口取不到、前端也填不了）。这里补上录入入口，功能才算完整。
  repositoryUrl: props.project?.repositoryUrl || '',
  endDate: props.project?.endDate || '',
  // 访问加密：none-公开 / repo-只加密仓库地址 / project-整项目加密
  lockLevel: props.project?.lockLevel || 'none',
  // 编辑已有加密项目时留空表示沿用原密码；新建或改密码时才填
  lockPassword: ''
})
const errors = reactive({
  title: '',
  description: '',
  categoryId: '',
  repositoryUrl: '',
  endDate: '',
  lockPassword: ''
})
const tagInput = ref('')
const coverBroken = ref(false)
const submitting = ref(false)

// ---- 访问加密 ----
// 三种形态：公开 / 只锁仓库地址 / 锁住整份项目档案
const LOCK_OPTIONS = [
  { value: 'none', icon: 'globe', title: '公开项目', desc: '所有人可见，仓库地址直接展示' },
  { value: 'repo', icon: 'lock', title: '加密仓库', desc: '项目内容公开，仓库地址需密码查看' },
  { value: 'project', icon: 'shield', title: '加密整个项目', desc: '介绍、标签与仓库都需密码才能查看' }
]
const LOCK_PASSWORD_MIN_LENGTH = 6
const LOCK_PASSWORD_MAX_LENGTH = 64
const lockPasswordId = 'lock-password'

// 每个账号最多 1 个加密项目：后端只回「已占用的那个项目」，
// 编辑它自己时不算占用，否则改密码也会被自己的配额挡住
const encryptionStatus = ref(null)
const encryptedElsewhere = computed(() => {
  const other = encryptionStatus.value?.project
  if (!other) return null
  if (isEdit.value && Number(other.id) === Number(props.project?.id)) return null
  return other
})
const canChooseEncryption = computed(() => !encryptedElsewhere.value)

// 新建加密项目必须设密码；编辑一个本来就加密的项目时可以留空沿用原密码
const needsNewLockPassword = computed(
  () =>
    form.lockLevel !== 'none' &&
    !(isEdit.value && props.project?.lockLevel && props.project.lockLevel !== 'none')
)

const selectLockLevel = (level) => {
  if (level !== 'none' && !canChooseEncryption.value) return
  form.lockLevel = level
  errors.lockPassword = ''
  if (level === 'none') {
    form.lockPassword = ''
    errors.repositoryUrl = validateRepositoryUrl(form.repositoryUrl)
  }
}

// ---- 实时预览 ----
const selectedCategory = computed(
  () => categories.value.find((cat) => cat.id === form.categoryId) || null
)
const previewTitle = computed(() => form.title || '你的项目标题')
const previewDescription = computed(
  () => form.description || '在这里写下你想做的事、为什么想做，以及希望遇见怎样的伙伴。'
)
const previewPlaceholder = computed(() => coverPalette(props.project?.id ?? 0))

// 准备度只统计真正影响卡片可读性的四项；仓库 / 截止日期是加分项，不计入
const completion = computed(() => [
  { label: '项目标题', done: form.title.trim().length >= 4, hint: '≥ 4 字' },
  { label: '项目分类', done: !!form.categoryId, hint: '必选' },
  { label: '项目介绍', done: form.description.trim().length >= 20, hint: '≥ 20 字' },
  { label: '封面图片', done: !!form.coverImage && !coverBroken.value, hint: '选填' }
])
const completedCount = computed(() => completion.value.filter((item) => item.done).length)
const progress = computed(() => Math.round((completedCount.value / completion.value.length) * 100))

// ---- 封面上传 ----
const fileInput = ref(null)
const uploading = ref(false)
const dragging = ref(false)
// 编辑态回填的是外链（而不是本站上传的 /uploads/...）时，直接把链接输入框展开，
// 否则用户看到封面却找不到改它的地方
const isUploadedCover = (url) => !!url && url.startsWith('/uploads/')
const showUrlInput = ref(!!props.project?.coverImage && !isUploadedCover(props.project.coverImage))

const pickFile = () => {
  if (uploading.value) return
  fileInput.value?.click()
}

// 清空 input.value：同一个文件连选两次也要能再次触发 change（否则浏览器不发第二次事件）
const onFileChange = (e) => {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (file) handleFile(file)
}

const onDrop = (e) => {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

const handleFile = async (file) => {
  // 类型先拦一道：这个压不回来，当场说清楚
  if (!COVER_ACCEPT.includes(file.type)) {
    toast('只支持 JPG / PNG / WebP / GIF 格式的图片', 'error')
    return
  }

  uploading.value = true
  try {
    // 大图先在本机压一遍再上传。手机原图动辄 6~10MB，旧流程把用户挡在 5MB 上限外、
    // 只能自己去找工具压 —— 这一步替他们做掉。
    // 压缩是「尽力而为」：解不出来（冷门格式 / 损坏文件）就原样传，交给下面那行体积校验。
    const { file: prepared, compressed, originalBytes } = await compressImage(file)

    // 体积校验挪到压缩**之后**：压完还超限才算真的超限。
    // （GIF 不参与压缩，走的就是这一条 —— 动图被重编码成静帧比超限被拒更糟）
    if (prepared.size > COVER_MAX_BYTES) {
      toast('图片不能超过 5MB，请压缩后再上传', 'error')
      return
    }

    const res = await uploadCover(prepared)
    form.coverImage = res.data.url
    // 记下原图，供「调整构图」反复从它出发
    rawCoverUrl.value = res.data.url
    coverBroken.value = false
    toast(
      compressed
        ? `封面已上传（已自动压缩 ${formatBytes(originalBytes)} → ${formatBytes(prepared.size)}）`
        : '封面已上传'
    )
  } catch {
    // 服务端拒绝的原因（魔数不符 / 超限）已由拦截器提示
  } finally {
    uploading.value = false
  }
}

// ---- 调整构图 ----
// 三条同时成立才给裁剪入口：
//   · 封面必须是本站上传的 —— 外链图跨源会污染 canvas，toBlob 直接抛 SecurityError
//   · 不能是 GIF —— canvas 只画得出第一帧，裁一次就把动图静默变成静帧
//   · 图得是能加载的 —— 已经坏掉的图裁出来只会是一张空白
const cropping = ref(false)
// 记住「本轮用户亲手传上去的那张原图」。裁完上传会换掉 form.coverImage，
// 但下一次裁剪必须**仍然从原图出发** —— 否则每调一次就再切一刀，
// 用户想「往回收一点」时已经收不回来了（被裁掉的像素服务端也拿不回来）。
// 编辑已有项目时没有原图（rawCoverUrl 为空），那时就只能以当前离线为准。
const rawCoverUrl = ref('')
const cropSource = computed(() =>
  isUploadedCover(form.coverImage) ? rawCoverUrl.value || form.coverImage : ''
)
const canCrop = computed(
  () => !!cropSource.value && !/\.gif(\?|$)/i.test(cropSource.value) && !coverBroken.value
)

const applyCrop = async ({ file }) => {
  uploading.value = true
  try {
    // 裁完必然比原图小，但这道闸门不靠「必然」—— 服务端也会独立校验体积与文件头
    if (file.size > COVER_MAX_BYTES) {
      toast('裁剪后的图片超过 5MB，请换一张', 'error')
      return
    }
    const res = await uploadCover(file)
    form.coverImage = res.data.url
    coverBroken.value = false
    cropping.value = false
    toast(`封面已按 ${COVER_ASPECT_LABEL} 重新构图`)
  } catch {
    // 上传失败时把用户留在裁剪界面，可以直接重试，不必重新选图
  } finally {
    uploading.value = false
  }
}

const removeCover = () => {
  form.coverImage = ''
  rawCoverUrl.value = ''
  coverBroken.value = false
  if (fileInput.value) fileInput.value.value = ''
}

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

// 仓库地址：只认 http/https。与后端 cleanRepositoryUrl 同口径 ——
// `javascript:` / `data:` 伪协议是 XSS 执行入口，两侧都要拦，前端这道是为了即时反馈，
// 后端那道才是结构性的（前端过滤会被绕过，比如直接打接口）。
const validateRepositoryUrl = (raw) => {
  const url = String(raw || '').trim()
  if (!url) return ''
  if (!/^https?:\/\/\S+$/i.test(url)) return '仓库地址需以 http:// 或 https:// 开头'
  if (url.length > 255) return '仓库地址最多 255 个字符'
  return ''
}

// 截止日期：格式 + 真实性双查。
// 真实性用「构造一个 Date 再读回年月日」来判，而不是 new Date('2026-02-31') —
// JS 会把 2 月 31 日悄悄滚到 3 月 3 日，2026-02-31 会被当成合法日期收下。
const validateEndDate = (raw) => {
  const date = String(raw || '').trim()
  if (!date) return ''
  const m = date.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return '截止日期格式应为 YYYY-MM-DD'
  const [, y, mo, d] = m
  const probe = new Date(`${date}T00:00:00Z`)
  if (Number.isNaN(probe.getTime()) || probe.getUTCFullYear() !== Number(y) ||
      probe.getUTCMonth() + 1 !== Number(mo) || probe.getUTCDate() !== Number(d)) {
    return '截止日期不是一个真实存在的日期'
  }
  return ''
}

const validate = () => {
  errors.title = form.title.length >= 4 ? '' : '标题至少 4 个字符'
  errors.categoryId = form.categoryId ? '' : '请选择一个项目分类'
  errors.description = form.description.length >= 20 ? '' : '介绍至少 20 个字符，多写一点更容易吸引伙伴'
  errors.repositoryUrl = validateRepositoryUrl(form.repositoryUrl)
  errors.endDate = validateEndDate(form.endDate)
  // 仓库加密必须有仓库可锁，否则密码锁住的只是一片空气
  if (form.lockLevel === 'repo' && !errors.repositoryUrl && !form.repositoryUrl.trim()) {
    errors.repositoryUrl = '加密仓库需要先填写仓库地址'
  }

  errors.lockPassword = ''
  if (form.lockLevel !== 'none' && (needsNewLockPassword.value || form.lockPassword)) {
    const length = form.lockPassword.length
    if (length < LOCK_PASSWORD_MIN_LENGTH) {
      errors.lockPassword = `访问密码至少 ${LOCK_PASSWORD_MIN_LENGTH} 位`
    } else if (length > LOCK_PASSWORD_MAX_LENGTH) {
      errors.lockPassword = `访问密码最多 ${LOCK_PASSWORD_MAX_LENGTH} 位`
    }
  }

  return !errors.title && !errors.categoryId && !errors.description &&
    !errors.repositoryUrl && !errors.endDate && !errors.lockPassword
}

const handleCancel = () => {
  if (isEdit.value) router.push(`/project/${props.project.id}`)
  else router.back()
}

const handleSubmit = async () => {
  addTagFromInput() // 提交前收纳未回车的标签
  // 封面上传还没落地就提交，会存下一个空封面 —— 等它传完再说
  if (uploading.value || !validate() || submitting.value) return
  // 配额兜底：状态还没拉回来或用户在别处已占用时，不让请求白跑一趟
  if (form.lockLevel !== 'none' && !canChooseEncryption.value) {
    toast('每个账号最多只能创建 1 个加密项目', 'error')
    return
  }

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
      coverImage: coverBroken.value ? '' : form.coverImage,
      // 空串而非 null：后端把空串视为「清空」，这样编辑时留空就能真的清掉这两项
      repositoryUrl: form.repositoryUrl.trim(),
      endDate: form.endDate.trim(),
      lockLevel: form.lockLevel,
      // 空密码不传：编辑已有加密项目时表示沿用原密码
      ...(form.lockLevel !== 'none' && form.lockPassword
        ? { lockPassword: form.lockPassword }
        : {})
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
  // 配额状态失败不阻塞发布：真超了后端还会再拦一次
  getEncryptionStatus()
    .then((res) => {
      encryptionStatus.value = res.data || null
    })
    .catch(() => {})
})
</script>

<style scoped>
/* ============ 窗口外壳 ============ */
.publish-window {
  position: relative;
  background: rgb(var(--c-cream));
  border: 1.5px solid rgb(var(--c-ink) / 0.16);
  border-radius: 20px 24px 18px 26px / 24px 18px 26px 20px;
  box-shadow: 6px 7px 0 rgb(var(--c-pine) / 0.14);
}

.publish-window__bar {
  @apply flex items-center justify-between gap-4 border-b border-line px-5 py-3.5 sm:px-7 sm:py-4;
  background: rgb(var(--c-sand) / 0.42);
  border-top-left-radius: inherit;
  border-top-right-radius: inherit;
}

.window-dots {
  @apply flex shrink-0 items-center gap-1.5;
}
.window-dot {
  @apply block h-2.5 w-2.5 rounded-full;
  border: 1px solid rgb(var(--c-ink) / 0.12);
}
.window-dot--pine { background: rgb(var(--c-pine) / 0.55); }
.window-dot--amber { background: rgb(var(--c-amber-warm) / 0.45); }
.window-dot--clay { background: rgb(var(--c-clay) / 0.4); }

.window-close {
  @apply flex h-8 w-8 items-center justify-center rounded-full text-ink-dim transition-colors hover:bg-sand hover:text-ink;
  border: 1px solid rgb(var(--c-ink) / 0.1);
}

.publish-window__footer {
  @apply sticky bottom-0 z-20 flex flex-wrap items-center gap-3 border-t border-line px-5 py-3.5 sm:px-7;
  background: rgb(var(--c-cream) / 0.94);
  backdrop-filter: blur(14px) saturate(1.4);
  border-bottom-left-radius: inherit;
  border-bottom-right-radius: inherit;
}

/* ============ 表单分段 ============ */
.form-section + .form-section {
  @apply mt-8 border-t border-dashed border-line pt-8;
}

.form-section__head {
  @apply flex items-start gap-3;
}

.step-index {
  @apply flex h-8 w-8 shrink-0 items-center justify-center font-mono text-caption1 font-semibold tabular-nums;
  color: rgb(var(--c-pine));
  border: 1px solid rgb(var(--c-pine) / 0.35);
  border-radius: 9px 12px 8px 11px / 11px 8px 12px 9px;
  background: rgb(var(--c-pine-soft) / 0.6);
}

.title-input {
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
  font-family: 'LXGW WenKai', 'Kaiti SC', 'STKaiti', KaiTi, 'Songti SC', serif;
  font-size: 1.25rem;
  line-height: 1.5rem;
  font-weight: 600;
  border-radius: var(--sketch-radius-md);
}

.input-counter {
  @apply pointer-events-none absolute bottom-2.5 right-3 font-mono text-caption2 tabular-nums text-ink-dim;
}

/* 分类选择：纸面小卡，选中后墨底反白 */
.category-option {
  @apply flex min-h-11 items-center gap-2.5 rounded-10 px-3 py-2 text-left text-ink transition-all duration-150;
  border: 1.5px solid rgb(var(--c-line));
  background: rgb(var(--c-cream));
}
.category-option:hover {
  border-color: rgb(var(--c-ink) / 0.28);
  background: rgb(var(--c-sand) / 0.5);
}
.category-option.is-active {
  border-color: rgb(var(--c-ink) / 0.7);
  background: rgb(var(--c-ink));
  color: rgb(var(--c-cream));
  box-shadow: 2px 2px 0 rgb(var(--c-pine) / 0.25);
}
.category-option__icon {
  @apply flex h-7 w-7 shrink-0 items-center justify-center rounded-full;
  background: rgb(var(--c-sand) / 0.8);
  color: rgb(var(--c-ink-mid));
}
.category-option.is-active .category-option__icon {
  background: rgb(var(--c-cream) / 0.12);
  color: rgb(var(--c-cream));
}

/* 访问加密：与分类小卡同一种纸面逻辑，但选项自带两行说明 */
.lock-option {
  @apply flex min-h-11 items-start gap-2.5 rounded-10 px-3 py-2.5 text-left text-ink transition-all duration-150;
  border: 1.5px solid rgb(var(--c-line));
  background: rgb(var(--c-cream));
}
.lock-option:hover {
  border-color: rgb(var(--c-ink) / 0.28);
  background: rgb(var(--c-sand) / 0.5);
}
.lock-option.is-active {
  border-color: rgb(var(--c-ink) / 0.7);
  background: rgb(var(--c-ink));
  color: rgb(var(--c-cream));
  box-shadow: 2px 2px 0 rgb(var(--c-pine) / 0.25);
}
.lock-option.is-disabled {
  @apply cursor-not-allowed opacity-45;
}
.lock-option.is-disabled:hover {
  border-color: rgb(var(--c-line));
  background: rgb(var(--c-cream));
}
.lock-option__icon {
  @apply flex h-7 w-7 shrink-0 items-center justify-center rounded-full;
  background: rgb(var(--c-sand) / 0.8);
  color: rgb(var(--c-ink-mid));
}
.lock-option.is-active .lock-option__icon {
  background: rgb(var(--c-cream) / 0.12);
  color: rgb(var(--c-cream));
}
.lock-option.is-active .text-ink-dim {
  color: rgb(var(--c-cream) / 0.72);
}

.lock-password-box {
  @apply rounded-14 px-4 py-4;
  border: 1.5px dashed rgb(var(--c-line-strong));
  background: rgb(var(--c-pine-tint) / 0.7);
}

.tag-field {
  @apply flex flex-wrap items-center gap-2 rounded-10 px-3 py-2 transition-all;
  border: 1.5px solid rgb(var(--c-line));
  background: rgb(var(--c-cream));
}
.tag-field:focus-within {
  border-color: rgb(var(--c-pine));
  box-shadow: 0 0 0 4px rgb(var(--c-pine) / 0.1);
}

/* ============ 封面上传 ============ */
.cover-drop {
  @apply min-h-[200px];
}
.cover-drop__icon {
  @apply flex h-11 w-11 items-center justify-center rounded-full;
  color: rgb(var(--c-pine));
  border: 1.5px dashed rgb(var(--c-pine) / 0.45);
  background: rgb(var(--c-pine-soft) / 0.5);
}

.cover-action {
  @apply rounded-full px-3 py-1.5 text-caption1 font-medium text-ink shadow-sm transition-colors hover:text-pine;
  background: rgb(var(--c-cream) / 0.92);
  backdrop-filter: blur(8px);
  border: 1px solid rgb(var(--c-ink) / 0.1);
}
.cover-action--danger:hover {
  color: rgb(var(--c-clay));
}

/* 预览图上的比例标记：说明这块就是广场卡片的封面，不是普通预览 */
.cover-card-mark {
  @apply pointer-events-none absolute left-3 top-3 rounded-full px-2.5 py-0.5 font-mono text-caption2 uppercase tracking-[0.1em] text-white;
  background: rgba(8, 9, 12, 0.72);
  border: 1px solid rgba(91, 224, 235, 0.2);
  backdrop-filter: blur(6px);
}

/* 常驻的裁剪入口：点开就是卡片取景框，不是另一个设置面板 */
.cover-crop-bar {
  @apply mt-2 flex min-h-11 w-full items-center gap-3 rounded-14 px-3 py-2.5 text-left transition-colors;
  border: 1.5px dashed rgb(var(--c-line-strong));
  background: rgb(var(--c-pine-tint) / 0.8);
}
.cover-crop-bar:hover {
  border-color: rgb(var(--c-pine) / 0.55);
  background: rgb(var(--c-pine-soft) / 0.55);
}
.cover-crop-bar__icon {
  @apply flex h-9 w-9 shrink-0 items-center justify-center rounded-full;
  color: rgb(var(--c-pine));
  border: 1.5px solid rgb(var(--c-pine) / 0.35);
  background: rgb(var(--c-cream) / 0.8);
}

/* ============ 右侧预览 ============ */
.preview-rail {
  border-left: 1.5px solid rgb(var(--c-line) / 0.75);
  background:
    linear-gradient(to bottom, rgb(var(--c-pine-tint) / 0.75), transparent 42%),
    rgb(var(--c-sand) / 0.18);
}

.preview-card {
  @apply overflow-hidden bg-cream transition-all duration-300;
  border: 1.5px solid rgb(var(--c-ink) / 0.14);
  border-radius: 16px 20px 14px 22px / 20px 14px 22px 16px;
  box-shadow: 4px 5px 0 rgb(var(--c-ink) / 0.06);
}

.preview-category {
  @apply absolute bottom-2.5 left-2.5 rounded-full px-2.5 py-0.5 font-mono text-caption2 uppercase tracking-[0.1em] text-white;
  background: rgba(8, 9, 12, 0.72);
  border: 1px solid rgba(91, 224, 235, 0.2);
  backdrop-filter: blur(6px);
}

.progress-card {
  @apply bg-cream p-4;
  border: 1.5px solid rgb(var(--c-line));
  border-radius: 12px 16px 10px 18px / 16px 10px 18px 12px;
}
</style>
