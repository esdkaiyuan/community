// 模拟数据 - 用于开发阶段测试
export const mockCategories = [
  { id: 1, name: '技术开发', icon: 'Monitor', count: 128 },
  { id: 2, name: '设计创意', icon: 'Brush', count: 86 },
  { id: 3, name: '产品/运营', icon: 'ShoppingBag', count: 64 },
  { id: 4, name: '内容创作', icon: 'VideoCamera', count: 52 },
  { id: 5, name: '硬件/物联网', icon: 'Cpu', count: 38 },
  { id: 6, name: '研究学习', icon: 'Reading', count: 45 },
  { id: 7, name: '开源专区', icon: 'Share', count: 73 },
  { id: 8, name: '公益/社会创新', icon: 'Handbag', count: 29 }
]

export const mockProjects = [
  {
    id: 1,
    title: '开源任务管理工具',
    description: '打造一个简洁易用的开源任务管理工具，支持多平台同步与团队协作。',
    coverImage: 'https://picsum.photos/seed/task1/400/300',
    categoryName: '技术开发',
    tags: ['开发', '开源', '效率工具'],
    participantCount: 12,
    likeCount: 1200,
    commentCount: 32,
    isRecommend: true,
    isHot: false,
    creator: {
      username: '张三',
      avatar: ''
    }
  },
  {
    id: 2,
    title: '环保知识科普小程序',
    description: '通过趣味互动的方式，向大众普及环保知识，共建绿色未来。',
    coverImage: 'https://picsum.photos/seed/eco2/400/300',
    categoryName: '设计创意',
    tags: ['设计', '小程序', '公益'],
    participantCount: 8,
    likeCount: 980,
    commentCount: 18,
    isRecommend: false,
    isHot: true,
    creator: {
      username: '李四',
      avatar: ''
    }
  },
  {
    id: 3,
    title: 'AI 助手插件开发',
    description: '开发一个浏览器插件，集成 AI 能力，提升信息获取与处理效率。',
    coverImage: 'https://picsum.photos/seed/ai3/400/300',
    categoryName: '技术开发',
    tags: ['开发', 'AI', '效率工具'],
    participantCount: 15,
    likeCount: 1500,
    commentCount: 45,
    isRecommend: true,
    isHot: true,
    creator: {
      username: '王五',
      avatar: ''
    }
  },
  {
    id: 4,
    title: '摄影作品分享平台',
    description: '一个专注于摄影作品分享与交流的平台，发现美，记录美。',
    coverImage: 'https://picsum.photos/seed/photo4/400/300',
    categoryName: '设计创意',
    tags: ['设计', '开发', '社区'],
    participantCount: 7,
    likeCount: 860,
    commentCount: 21,
    isRecommend: false,
    isHot: false,
    creator: {
      username: '赵六',
      avatar: ''
    }
  },
  {
    id: 5,
    title: '智能家居控制系统',
    description: '基于物联网技术，实现家居设备的智能控制与自动化场景。',
    coverImage: 'https://picsum.photos/seed/smart5/400/300',
    categoryName: '硬件/物联网',
    tags: ['硬件', '物联网', '智能家居'],
    participantCount: 10,
    likeCount: 1100,
    commentCount: 29,
    isRecommend: false,
    isHot: false,
    creator: {
      username: '钱七',
      avatar: ''
    }
  },
  {
    id: 6,
    title: '在线学习笔记协作平台',
    description: '支持多人协作的在线学习笔记工具，让学习更高效。',
    coverImage: 'https://picsum.photos/seed/study6/400/300',
    categoryName: '研究学习',
    tags: ['产品', '教育', '协作'],
    participantCount: 6,
    likeCount: 730,
    commentCount: 16,
    isRecommend: false,
    isHot: false,
    creator: {
      username: '孙八',
      avatar: ''
    }
  },
  {
    id: 7,
    title: '独立游戏《遗忘之境》',
    description: '一款像素风冒险解谜游戏，探索遗忘之地的秘密。',
    coverImage: 'https://picsum.photos/seed/game7/400/300',
    categoryName: '设计创意',
    tags: ['游戏开发', '像素风', '独立游戏'],
    participantCount: 20,
    likeCount: 2300,
    commentCount: 68,
    isRecommend: true,
    isHot: true,
    creator: {
      username: '周九',
      avatar: ''
    }
  },
  {
    id: 8,
    title: '开源字体设计计划',
    description: '打造一套开放、可商用的高质量中文字体，服务广大设计师。',
    coverImage: 'https://picsum.photos/seed/font8/400/300',
    categoryName: '设计创意',
    tags: ['设计', '字体', '开源'],
    participantCount: 9,
    likeCount: 990,
    commentCount: 27,
    isRecommend: false,
    isHot: false,
    creator: {
      username: '吴十',
      avatar: ''
    }
  }
]
