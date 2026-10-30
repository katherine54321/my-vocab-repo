# VocabMatrix Cloud Database (my-vocab-repo)

> 🚀 开源只读静态英语词库中心，基于 **GitHub + jsDelivr / Cloudflare Pages** 零成本高速 CDN 分发。
> 收录 **14,200** 个经由 CEFR (A1-C2) 权威分级的多场景词汇切片。

## 📁 目录结构
```text
my-vocab-repo/
├── categories.json               # 场景树索引清单（涵盖学科、人类、食物、社会等各分类词数与难度分布）
└── data/
    ├── psychology.json           # 心理学分类词汇
    ├── human_organs.json         # 人体器官分类词汇
    ├── food_dining.json          # 餐饮与食物分类词汇
    └── ... (共 22 个场景静态切片)
```

## ⚡ 如何通过 CDN 毫秒级全球加速访问
借助免费的 jsDelivr CDN 代理访问 GitHub 原始文件，避免 GitHub API 限流并获得全球 CDN 边缘节点缓存加速：

### 1. 获取全景场景树索引：
```http
GET https://cdn.jsdelivr.net/gh/<你的GitHub用户名>/my-vocab-repo@main/categories.json
```

### 2. 按需动态加载各学科/场景切片：
```http
GET https://cdn.jsdelivr.net/gh/<你的GitHub用户名>/my-vocab-repo@main/data/psychology.json
GET https://cdn.jsdelivr.net/gh/<你的GitHub用户名>/my-vocab-repo@main/data/human_organs.json
GET https://cdn.jsdelivr.net/gh/<你的GitHub用户名>/my-vocab-repo@main/data/food_dining.json
```

## 🛠️ 推送至你的 GitHub 仓库步骤
```bash
cd my-vocab-repo
git init
git add .
git commit -m "feat: publish 14,000+ CEFR English vocabulary database"
git branch -M main
git remote add origin https://github.com/<你的GitHub用户名>/my-vocab-repo.git
git push -u origin main
```
