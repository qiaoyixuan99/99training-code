// ──────────────────────────────────────
// Daily Forge — 任务学习资源库
// 每个任务的详细内容、参考链接、学习指导
// ──────────────────────────────────────

const TASK_RESOURCES = {
  morning: {
    id: 'morning',
    title: '语法 + 泛听',
    subtitle: 'Cambridge Grammar + BBC Listening',
    icon: '🌅',
    overview: '每天上午花1小时，通过剑桥雅思语法书系统学习语法点，同时用BBC泛听保持英语语感。语法是骨架，听力是血肉，两者缺一不可。',
    sections: [
      {
        title: '📖 Cambridge Grammar for IELTS',
        type: 'study',
        content: '这本书覆盖雅思考试所有核心语法点，每个单元包含讲解+练习。建议每天完成1个单元，先看讲解再做练习，错题用红笔标注。',
        steps: [
          '阅读本单元语法讲解（约10分钟）',
          '完成配套练习题（约20分钟）',
          '核对答案，标注错题',
          '总结本单元核心规则，写在笔记本上',
        ],
        resources: [
          { name: '📖 Cambridge Grammar for IELTS 电子版', url: 'https://www.cambridge.org/elt/grammarforielts', type: 'book' },
          { name: '📝 IELTS Grammar 配套练习', url: 'https://ieltsliz.com/ielts-grammar/', type: 'practice' },
          { name: '🎯 Grammar in Use 系列官网', url: 'https://www.cambridge.org/grammarinuse', type: 'reference' },
        ],
      },
      {
        title: '🎧 BBC World Service 泛听',
        type: 'listen',
        content: '泛听的目标不是听懂每个词，而是保持对英语语音、语调、节奏的敏感度。选择感兴趣的话题，边听边做其他事（如洗漱、吃早餐）。',
        steps: [
          '打开BBC World Service直播或播客',
          '不需要100%专注，让英语成为背景音',
          '遇到感兴趣的话题时可以精听2-3分钟',
          '记录1-2个新听到的表达或词汇',
        ],
        resources: [
          { name: '📻 BBC World Service 直播', url: 'https://www.bbc.co.uk/sounds/play/live:bbc_world_service', type: 'audio' },
          { name: '🎧 BBC Learning English 播客', url: 'https://www.bbc.co.uk/learningenglish', type: 'podcast' },
          { name: '📰 BBC News 简易英语', url: 'https://www.bbc.co.uk/newsround', type: 'reading' },
          { name: '🎬 BBC 6 Minute English', url: 'https://www.bbc.co.uk/learningenglish/english/features/6-minute-english', type: 'podcast' },
        ],
      },
      {
        title: '💡 语法学习技巧',
        type: 'tips',
        content: '高效语法学习的关键是"理解规则 → 大量练习 → 错题复盘"的闭环。',
        tips: [
          '不要死记规则，通过例句理解用法',
          '每学完一个语法点，造3个自己的句子',
          '建立"语法错题本"，每周回顾一次',
          '写作时刻意使用新学的语法结构',
          '对比中英文语法差异，加深理解',
        ],
      },
    ],
  },

  noon: {
    id: 'noon',
    title: '词汇突击',
    subtitle: 'Anki 雅思核心词库',
    icon: '☀️',
    overview: '每天中午花20分钟，用Anki间隔重复法高效记忆雅思核心词汇。新词15个+复习旧词，重点攻克昨天出错的词汇。词汇是所有英语能力的基础。',
    sections: [
      {
        title: '📚 Anki 词库使用',
        type: 'study',
        content: 'Anki基于艾宾浩斯遗忘曲线，在你即将忘记时自动安排复习。每天新学15个词+复习系统推荐的旧词，是最高效的词汇学习方式。',
        steps: [
          '打开Anki，选择"雅思核心词汇"牌组',
          '先复习系统推荐的旧词（通常20-40个）',
          '学习15个新词，注意例句和发音',
          '重点关注昨天标记为"困难"的词汇',
          '完成当日学习后，检查统计面板',
        ],
        resources: [
          { name: '📥 Anki 官网下载', url: 'https://apps.ankiweb.net/', type: 'tool' },
          { name: '🃏 雅思核心词库 (AnkiWeb)', url: 'https://ankiweb.net/shared/decks?search=ielts', type: 'deck' },
          { name: '🃏 雅思高频词汇牌组', url: 'https://ankiweb.net/shared/decks?search=ielts%20vocabulary', type: 'deck' },
        ],
      },
      {
        title: '🧠 词汇记忆技巧',
        type: 'tips',
        content: '机械记忆效率低，用对方法事半功倍。',
        tips: [
          '词根词缀法：掌握常见前后缀（un-, re-, -tion, -ment）',
          '联想记忆：把新词和已知词/画面联系起来',
          '语境记忆：记住整个例句而非孤立单词',
          '词族扩展：学一个词时同步学其名词/动词/形容词形式',
          '间隔复习：今天学的词，第1/3/7/14天各复习一次',
          '主动使用：学完新词后，在写作或口语中刻意使用',
        ],
      },
      {
        title: '📝 雅思高频词汇分类',
        type: 'reference',
        content: '雅思考试中出现频率最高的词汇分类整理，优先掌握这些。',
        categories: [
          { name: '教育类', words: 'curriculum, syllabus, academic, scholarship, enrollment, tuition, dissertation, faculty, semester, assessment' },
          { name: '科技类', words: 'innovation, automation, artificial intelligence, algorithm, database, bandwidth, cybersecurity, digitalization' },
          { name: '环境类', words: 'sustainability, emission, ecosystem, biodiversity, renewable, conservation, deforestation, pollution' },
          { name: '社会类', words: 'demographic, inequality, urbanization, migration, infrastructure, welfare, legislation, unemployment' },
        ],
        resources: [
          { name: '📖 雅思词汇真经 (刘洪波)', url: 'https://book.douban.com/subject/27178508/', type: 'book' },
          { name: '📝 IELTS Vocabulary List', url: 'https://ieltsliz.com/ielts-vocabulary/', type: 'reference' },
        ],
      },
    ],
  },

  afternoon: {
    id: 'afternoon',
    title: '英文技术精读',
    subtitle: 'AI/Agent 方向技术文章',
    icon: '🌤️',
    overview: '每天下午花1小时精读1篇英文技术文章（AI/Agent方向），拆解3个长难句。精读不是浏览，是逐句理解、标注语法、积累表达。这是同时提升英语和技术认知的核心训练。',
    sections: [
      {
        title: '📰 推荐阅读源',
        type: 'study',
        content: '选择高质量的英文技术文章源，难度适中、内容前沿。',
        resources: [
          { name: '🤖 AI News - MIT Technology Review', url: 'https://www.technologyreview.com/topic/artificial-intelligence/', type: 'news' },
          { name: '📝 The Batch (Andrew Ng)', url: 'https://www.deeplearning.ai/the-batch/', type: 'newsletter' },
          { name: '🧠 Hugging Face Blog', url: 'https://huggingface.co/blog', type: 'blog' },
          { name: '📖 OpenAI Blog', url: 'https://openai.com/blog', type: 'blog' },
          { name: '🔗 LangChain Blog', url: 'https://blog.langchain.dev/', type: 'blog' },
          { name: '📊 Towards Data Science', url: 'https://towardsdatascience.com/', type: 'blog' },
          { name: '🗞️ Hacker News (AI标签)', url: 'https://news.ycombinator.com/', type: 'news' },
        ],
      },
      {
        title: '🔍 精读方法论',
        type: 'method',
        content: '精读的核心是"三遍法"：第一遍通读抓主旨，第二遍逐句精析，第三遍总结输出。',
        steps: [
          '【第一遍 · 5分钟】快速通读全文，理解主旨和结构',
          '【第二遍 · 35分钟】逐段精读，标注生词和长难句',
          '【长难句拆解】选出3个最复杂的句子，分析语法结构',
          '【词汇积累】记录5-8个技术领域高频词汇',
          '【第三遍 · 10分钟】用英文写3句话总结文章要点',
          '【输出】将总结和心得写入每日反思',
        ],
      },
      {
        title: '📐 长难句拆解模板',
        type: 'template',
        content: '遇到长句时，用这个模板逐步拆解：',
        template: [
          '1️⃣ 找主句：哪个是主语？哪个是谓语？',
          '2️⃣ 找从句：that/which/who引导的定语从句修饰谁？',
          '3️⃣ 找连接：and/but/or/however 连接了什么？',
          '4️⃣ 找插入：逗号之间的插入语可以先跳过',
          '5️⃣ 重组语序：把修饰成分去掉，只留主干',
        ],
        example: {
          original: 'The language model, which was trained on a diverse corpus of internet text, demonstrated remarkable capabilities in understanding context and generating coherent responses that closely mimicked human-like reasoning patterns.',
          analysis: '主干: The model demonstrated capabilities. 定语从句1: which was trained... 修饰 model. 介词短语: in understanding... and generating... 说明 capabilities 的范围. 定语从句2: that mimicked... 修饰 responses.',
          simplified: '这个语言模型在理解上下文和生成连贯回复方面表现出色，它是在大量互联网文本上训练的。',
        },
      },
    ],
  },

  evening: {
    id: 'evening',
    title: 'Agent 开发实战',
    subtitle: 'LangChain / RAG / AI Agent',
    icon: '🌙',
    overview: '每天晚上花1.5小时学习AI Agent开发。从LangChain基础到RAG系统再到多Agent架构，边学边写代码，每天产出可运行的结果。这是通往"AI工程师"第二职业的核心技能。',
    sections: [
      {
        title: '🎓 DeepLearning.AI 短课',
        type: 'study',
        content: 'DeepLearning.AI提供免费的LangChain/AI短课，每课1-2小时，由行业专家讲授。建议按顺序学习。',
        courses: [
          { name: 'LangChain for LLM Application Development', desc: 'LangChain基础：链、记忆、代理', url: 'https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/', difficulty: '入门' },
          { name: 'Building Systems with the ChatGPT API', desc: '用ChatGPT API构建完整系统', url: 'https://www.deeplearning.ai/short-courses/building-systems-with-chatgpt/', difficulty: '入门' },
          { name: 'Building Agentic RAG with LlamaIndex', desc: '用LlamaIndex构建Agent式RAG', url: 'https://www.deeplearning.ai/short-courses/building-agentic-rag-with-llamaindex/', difficulty: '中级' },
          { name: 'AI Agents in LangGraph', desc: '用LangGraph构建AI Agent', url: 'https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/', difficulty: '中级' },
          { name: 'Multi AI Agent Systems with CrewAI', desc: '多Agent系统设计与实现', url: 'https://www.deeplearning.ai/short-courses/multi-ai-agent-systems-with-crewai/', difficulty: '高级' },
        ],
        resources: [
          { name: '🎓 DeepLearning.AI 全部短课', url: 'https://www.deeplearning.ai/short-courses/', type: 'course' },
        ],
      },
      {
        title: '⛓️ LangChain 学习路径',
        type: 'roadmap',
        content: 'LangChain是目前最流行的LLM应用开发框架，掌握它是Agent开发的基础。',
        steps: [
          '【Week 1-2】基础概念：LLM、Prompt Template、Output Parser',
          '【Week 3-4】Chain构建：Sequential Chain、Router Chain',
          '【Week 5-6】RAG系统：文档加载、向量化、检索、问答',
          '【Week 7-8】Agent：Tools、Agent Executor、ReAct模式',
          '【Week 9-10】LangGraph：状态机、条件分支、人机协作',
          '【Week 11-12】实战项目：构建一个完整的AI助手',
        ],
        resources: [
          { name: '📖 LangChain 官方文档', url: 'https://python.langchain.com/docs/get_started/introduction', type: 'docs' },
          { name: '📖 LangChain GitHub', url: 'https://github.com/langchain-ai/langchain', type: 'code' },
          { name: '📖 LangGraph 文档', url: 'https://langchain-ai.github.io/langgraph/', type: 'docs' },
          { name: '🎬 LangChain YouTube 教程', url: 'https://www.youtube.com/@LangChain', type: 'video' },
        ],
      },
      {
        title: '🔧 实战代码参考',
        type: 'code',
        content: '每天写代码，产出可运行的结果。以下是常见代码模板和参考项目。',
        resources: [
          { name: '💻 RAG 入门模板', url: 'https://github.com/langchain-ai/rag-from-scratch', type: 'code' },
          { name: '💻 Agent 模板项目', url: 'https://github.com/langchain-ai/langchain-template', type: 'code' },
          { name: '💻 LangGraph 示例集', url: 'https://github.com/langchain-ai/langgraph/tree/main/examples', type: 'code' },
          { name: '💻 OpenAI Cookbook', url: 'https://github.com/openai/openai-cookbook', type: 'code' },
          { name: '📖 ChromaDB (向量数据库)', url: 'https://docs.trychroma.com/', type: 'docs' },
          { name: '📖 Pinecone 文档', url: 'https://docs.pinecone.io/', type: 'docs' },
        ],
      },
      {
        title: '🗺️ Agent 开发学习路线图',
        type: 'roadmap',
        content: '从零到能独立开发AI Agent系统的完整路径。',
        milestones: [
          { level: 'Lv.1-3', title: '基础阶段', items: ['Python基础 + API调用', 'Prompt Engineering', 'LangChain基础链'] },
          { level: 'Lv.4-6', title: 'RAG阶段', items: ['向量数据库', '文档检索系统', '多源RAG'] },
          { level: 'Lv.7-9', title: 'Agent阶段', items: ['ReAct Agent', '工具调用', '多Agent协作'] },
          { level: 'Lv.10-12', title: '系统设计', items: ['Agent架构设计', '生产部署', '评估与优化'] },
          { level: 'Lv.13-15', title: '商业化', items: ['独立开发产品', '接单/咨询', '第二职业就绪'] },
        ],
      },
    ],
  },
};

module.exports = { TASK_RESOURCES };
