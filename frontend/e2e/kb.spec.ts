import { expect, test, type Browser, type Page } from "@playwright/test"

const unique = () => Date.now().toString(36)

async function createAuthedContext(browser: Browser): Promise<Page> {
  const context = await browser.newContext()
  const page = await context.newPage()

  // Navigate to set origin, then inject localStorage tokens
  await page.goto("/")

  const ls = globalThis.__e2eLocalStorage as Record<string, string> | undefined
  if (ls) {
    await page.evaluate((data) => {
      for (const [key, value] of Object.entries(data)) {
        localStorage.setItem(key, value)
      }
    }, ls)
  }

  return page
}

test.describe("Knowledge Base", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage()

    // Register
    const username = `kb${unique()}`
    globalThis.__e2eUsername = username
    await page.goto("/auth/register")
    await page.getByTestId("username-input").fill(username)
    await page.getByTestId("email-input").fill(`${username}@test.com`)
    await page.getByTestId("password-input").fill("Testpass123")
    await page.getByTestId("confirm-password-input").fill("Testpass123")
    await page.getByTestId("submit-button").click()
    await page.waitForURL("**/auth/login")

    // Login
    await page.getByTestId("username-input").fill(username)
    await page.getByTestId("password-input").fill("Testpass123")
    await page.getByTestId("submit-button").click()
    await page.waitForURL("**/")

    // Wait for auth to settle
    await page.waitForSelector("text=欢迎回到 Pivot 控制台")

    // Save localStorage for reuse
    globalThis.__e2eLocalStorage = await page.evaluate(() => {
      const data: Record<string, string> = {}
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key) data[key] = localStorage.getItem(key) ?? ""
      }
      return data
    })

    await page.close()
  })

  test("KB full flow", async ({ browser }) => {
    const page = await createAuthedContext(browser)

    // --- Sidebar ---
    await page.goto("/")
    await expect(page.getByRole("link", { name: "知识库" })).toBeVisible()

    // --- KB list (empty) ---
    await page.goto("/kb")
    await expect(page.getByTestId("kb-list")).toBeVisible()

    // --- Create KB ---
    const kbName = `E2E ${unique()}`
    await page.getByTestId("create-kb-button").click()
    await expect(page.getByTestId("kb-form-dialog")).toBeVisible()
    await page.getByTestId("kb-name-input").fill(kbName)
    await page.getByTestId("kb-description-input").fill("Created by E2E")
    await page.getByTestId("kb-form-dialog").getByTestId("submit-button").click()
    await expect(page.getByTestId("kb-form-dialog")).not.toBeVisible()
    await expect(page.getByText(kbName)).toBeVisible()

    // --- KB detail (empty docs) ---
    await page.getByText(kbName).click()
    await page.waitForURL("**/kb/*")
    await expect(page.getByText(kbName)).toBeVisible()
    await expect(page.getByText("还没有文档")).toBeVisible()

    // --- Upload document ---
    await page.getByTestId("upload-document-button").click()
    await expect(page.getByTestId("document-upload-dialog")).toBeVisible()
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: "hello.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Hello E2E"),
    })
    await page.getByTestId("document-upload-dialog").getByTestId("submit-button").click()
    await expect(page.getByTestId("document-upload-dialog")).not.toBeVisible()
    await expect(page.getByTestId("document-table").getByText("hello.txt")).toBeVisible()

    // --- Delete document ---
    const docDelBtn = page.locator('[data-testid^="doc-delete-button-"]').first()
    await docDelBtn.click()
    await expect(page.getByTestId("delete-confirm-dialog")).toBeVisible()
    await page.getByTestId("confirm-delete-button").click()
    await expect(page.getByTestId("delete-confirm-dialog")).not.toBeVisible()
    await expect(page.getByText("还没有文档")).toBeVisible()

    // --- Edit KB ---
    const updatedName = `E2E Up ${unique()}`
    await page.getByTestId("edit-kb-button").click()
    await expect(page.getByTestId("kb-form-dialog")).toBeVisible()
    await page.getByTestId("kb-name-input").clear()
    await page.getByTestId("kb-name-input").fill(updatedName)
    await page.getByTestId("kb-form-dialog").getByTestId("submit-button").click()
    await expect(page.getByTestId("kb-form-dialog")).not.toBeVisible()
    await expect(page.getByText(updatedName)).toBeVisible()

    // --- Delete KB ---
    await page.getByTestId("delete-kb-button").click()
    await expect(page.getByTestId("delete-confirm-dialog")).toBeVisible()
    await page.getByTestId("confirm-delete-button").click()
    await page.waitForURL("**/kb")

    await page.context().close()
  })
})

declare global {
  // eslint-disable-next-line no-var
  var __e2eLocalStorage: Record<string, string> | undefined
  // eslint-disable-next-line no-var
  var __e2eUsername: string | undefined
}
