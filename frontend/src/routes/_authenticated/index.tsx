import { createFileRoute } from "@tanstack/react-router"

import { useAuth } from "@/hooks/use-auth"

export const Route = createFileRoute("/_authenticated/")({
  component: DashboardPage,
})

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 6) return "夜深了"
  if (hour < 12) return "早上好"
  if (hour < 18) return "下午好"
  return "晚上好"
}

function formatDate() {
  return new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "long",
  })
}

const stats = [
  {
    label: "API 调用",
    value: "12,847",
    change: "+12%",
    changeLabel: "较上周",
    color: "bg-teal-500",
    colorLight: "bg-teal-50",
    colorText: "text-teal-600",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
  },
  {
    label: "知识库",
    value: "6",
    change: "+2",
    changeLabel: "本月新增",
    color: "bg-blue-500",
    colorLight: "bg-blue-50",
    colorText: "text-blue-600",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </svg>
    ),
  },
  {
    label: "文档数量",
    value: "128",
    change: "+24",
    changeLabel: "本月新增",
    color: "bg-amber-500",
    colorLight: "bg-amber-50",
    colorText: "text-amber-600",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <line x1="10" y1="9" x2="8" y2="9" />
      </svg>
    ),
  },
  {
    label: "对话次数",
    value: "42",
    change: "+8",
    changeLabel: "本周新增",
    color: "bg-purple-500",
    colorLight: "bg-purple-50",
    colorText: "text-purple-600",
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
      </svg>
    ),
  },
]

const quickActions = [
  {
    title: "创建知识库",
    description: "上传文档，构建 RAG 知识库",
    icon: (
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
        <path d="M12 12v8" />
        <path d="M8 16h8" />
      </svg>
    ),
  },
  {
    title: "开始对话",
    description: "基于知识库进行智能问答",
    icon: (
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
        <path d="M8 12h8" />
        <path d="M8 8h8" />
      </svg>
    ),
  },
  {
    title: "API 文档",
    description: "查看接口文档与集成指南",
    icon: (
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
        <line x1="14" y1="4" x2="10" y2="20" />
      </svg>
    ),
  },
]

const gettingStarted = [
  {
    step: "01",
    title: "创建知识库",
    description: "新建一个知识库来组织你的文档资源",
  },
  {
    step: "02",
    title: "上传文档",
    description: "支持 PDF、Word、Markdown 等多种格式",
  },
  {
    step: "03",
    title: "开始检索",
    description: "通过 API 或对话界面进行知识检索",
  },
]

function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="mx-auto max-w-6xl p-5 lg:p-8">
      <section className="animate-fade-up mb-8">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-text-primary lg:text-3xl">
              {getGreeting()}，{user?.username}
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              欢迎回到 Pivot 控制台
            </p>
            <div className="mt-3 h-0.5 w-12 rounded-full bg-gradient-to-r from-accent to-transparent" />
          </div>
          <p className="mt-2 text-sm text-text-muted sm:mt-0">{formatDate()}</p>
        </div>
      </section>

      <section className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <div
            key={stat.label}
            className="animate-fade-up rounded-xl border border-border-dim bg-white p-5"
            style={{ animationDelay: `${(i + 1) * 60}ms` }}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-text-muted">
                  {stat.label}
                </p>
                <p className="mt-2 font-display text-2xl font-bold text-text-primary">
                  {stat.value}
                </p>
              </div>
              <div className={`rounded-lg ${stat.colorLight} p-2.5`}>
                <span className={stat.colorText}>{stat.icon}</span>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-1.5 text-xs">
              <span className={`font-semibold ${stat.colorText}`}>
                {stat.change}
              </span>
              <span className="text-text-muted">{stat.changeLabel}</span>
            </div>
          </div>
        ))}
      </section>

      <section className="mb-8">
        <h2 className="mb-4 font-display text-lg font-semibold text-text-primary">
          快速开始
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {quickActions.map((action, i) => (
            <div
              key={action.title}
              className="group cursor-pointer rounded-xl border border-border-dim bg-white p-6 transition-all duration-200 hover:border-accent/30 hover:shadow-sm"
              style={{ animationDelay: `${(i + 5) * 60}ms` }}
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-dim text-accent transition-colors group-hover:bg-accent group-hover:text-white">
                {action.icon}
              </div>
              <h3 className="font-display font-semibold text-text-primary">
                {action.title}
              </h3>
              <p className="mt-1 text-sm leading-relaxed text-text-muted">
                {action.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-4 font-display text-lg font-semibold text-text-primary">
          使用指南
        </h2>
        <div className="rounded-xl border border-border-dim bg-white p-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {gettingStarted.map((item, i) => (
              <div key={item.step} className="flex items-start gap-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-white">
                  {item.step}
                </div>
                <div>
                  <h4 className="font-display font-semibold text-text-primary">
                    {item.title}
                  </h4>
                  <p className="mt-1 text-sm leading-relaxed text-text-muted">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
