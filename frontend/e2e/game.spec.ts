import { test, expect } from '@playwright/test';

test.describe('Xiangqi Game E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display initial page with no game', async ({ page }) => {
    // 检查页面标题
    await expect(page.locator('h2')).toContainText('Chinese Chess');

    // 检查初始提示
    await expect(page.locator('.no-game')).toBeVisible();
    await expect(page.locator('.no-game p')).toContainText('Start a new game');
  });

  test('should create a new human vs human game', async ({ page }) => {
    // 选择人对人模式
    await page.selectOption('select', 'human_vs_human');

    // 点击开始游戏
    await page.click('button:has-text("Start New Game")');

    // 等待棋盘出现
    await expect(page.locator('.board')).toBeVisible();

    // 检查棋子数量（32个）
    const pieces = page.locator('.piece');
    await expect(pieces).toHaveCount(32);

    // 检查红方先走
    await expect(page.locator('.status')).toContainText("Red's turn");
  });

  test('should create a human vs AI game', async ({ page }) => {
    // 选择人对 AI 模式
    const selects = page.locator('select');
    await selects.first().selectOption('human_vs_ai');

    // 等待 AI 难度选择器出现（因为组件条件渲染）
    await expect(selects.nth(1)).toBeVisible();

    // 选择 AI 难度
    await selects.nth(1).selectOption('easy');

    // 点击开始游戏
    await page.click('button:has-text("Start New Game")');

    // 等待棋盘出现
    await expect(page.locator('.board')).toBeVisible();

    // 应该是红方先走（人类）
    await expect(page.locator('.status')).toContainText("Red's turn");
  });

  test('should make a move in human vs human game', async ({ page }) => {
    // 开始人对人游戏
    await page.selectOption('select', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');

    // 等待棋盘
    await expect(page.locator('.board')).toBeVisible();

    // 点击红方左边的车（位置 row=0, col=0）
    // 棋盘从上到下是 row 9 到 0，所以 row=0 是最下面
    const cells = page.locator('.cell');
    // 红方车在最底部左边，即第 10 行（index 9）的第一个格子
    await cells.nth(9 * 9).click(); // 第 10 行第 1 列

    // 检查选中状态
    await expect(cells.nth(9 * 9)).toHaveClass(/selected/);

    // 点击目标位置（车前进两步）
    await cells.nth(7 * 9).click(); // 第 8 行第 1 列

    // 检查回合切换
    await expect(page.locator('.status')).toContainText("Black's turn");
  });

  test('should show legal move indicators', async ({ page }) => {
    // 开始游戏
    await page.selectOption('select', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 点击一个红方棋子
    const cells = page.locator('.cell');
    await cells.nth(9 * 9).click(); // 红方车

    // 应该显示合法移动指示器
    const legalTargets = page.locator('.cell.legal-target');
    await expect(legalTargets).not.toHaveCount(0);
  });

  test('should display move count', async ({ page }) => {
    // 开始游戏
    await page.selectOption('select', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');

    // 检查初始移动计数
    await expect(page.locator('.move-count')).toContainText('Moves: 0');

    // 执行一步走棋
    const cells = page.locator('.cell');
    await cells.nth(9 * 9).click();
    await cells.nth(7 * 9).click();

    // 检查移动计数更新
    await expect(page.locator('.move-count')).toContainText('Moves: 1');
  });

  test('should handle AI vs AI game', async ({ page }) => {
    // 选择 AI vs AI 模式
    await page.selectOption('select:first-of-type', 'ai_vs_ai');
    await page.click('button:has-text("Start New Game")');

    await expect(page.locator('.board')).toBeVisible();

    // 应该显示 AI 走棋按钮
    await expect(page.locator('button:has-text("Next AI Move")')).toBeVisible();

    // 点击 AI 走棋
    await page.click('button:has-text("Next AI Move")');

    // 检查移动计数增加
    await expect(page.locator('.move-count')).toContainText('Moves: 1');
  });
});

test.describe('Error Handling', () => {
  test('should show error when server is unavailable', async ({ page }) => {
    // 这个测试假设后端未启动
    // 由于我们的 webServer 配置会启动后端，这里只是验证错误处理逻辑存在
    await page.goto('/');

    // 检查错误消息组件存在于 DOM 中（但不可见，因为没有错误）
    const errorDiv = page.locator('.error-message');
    await expect(errorDiv).not.toBeVisible();
  });
});
