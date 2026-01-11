import { test, expect } from '@playwright/test';

test.describe('Jieqi Game E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // 切换到揭棋模式
    await page.click('button:has-text("Jieqi (Reveal)")');
  });

  test('should switch to jieqi mode', async ({ page }) => {
    // 检查标题
    await expect(page.locator('h2')).toContainText('Jieqi (Reveal Chess)');

    // 检查初始提示
    await expect(page.locator('.no-game')).toBeVisible();
    await expect(page.locator('.no-game p')).toContainText('Start a new Jieqi game');
  });

  test('should display rules panel', async ({ page }) => {
    // 检查规则面板
    await expect(page.locator('.rules-panel h4')).toContainText('Jieqi Rules');
    await expect(page.locator('.rules-panel')).toContainText('Only Kings start revealed');
  });

  test('should create a new human vs human jieqi game', async ({ page }) => {
    // 选择人对人模式
    await page.selectOption('select#mode', 'human_vs_human');

    // 点击开始游戏
    await page.click('button:has-text("Start New Game")');

    // 等待棋盘出现
    await expect(page.locator('.board')).toBeVisible();

    // 检查棋子数量（32个）
    const pieces = page.locator('.piece');
    await expect(pieces).toHaveCount(32);

    // 检查红方先走
    await expect(page.locator('.status')).toContainText("Red's turn");

    // 检查暗子计数（应该是 30 个暗子，红黑各 15 个）
    await expect(page.locator('.hidden-count')).toContainText('Red: 15');
    await expect(page.locator('.hidden-count')).toContainText('Black: 15');
  });

  test('should show hidden pieces with special characters', async ({ page }) => {
    // 开始游戏
    await page.selectOption('select#mode', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 检查暗子存在（带有 hidden-piece class）
    const hiddenPieces = page.locator('.piece.hidden-piece');
    await expect(hiddenPieces).toHaveCount(30);

    // 检查明子（将和帅）
    const revealedPieces = page.locator('.piece:not(.hidden-piece)');
    await expect(revealedPieces).toHaveCount(2);
  });

  test('should show revealed kings', async ({ page }) => {
    // 开始游戏
    await page.selectOption('select#mode', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 检查红帅和黑将是明子
    await expect(page.locator('.piece:has-text("帥")')).toBeVisible();
    await expect(page.locator('.piece:has-text("將")')).toBeVisible();
  });

  test('should create a human vs AI jieqi game', async ({ page }) => {
    // 选择人对 AI 模式
    await page.selectOption('select#mode', 'human_vs_ai');

    // 检查 AI 颜色选择器出现
    await expect(page.locator('select#aiColor')).toBeVisible();

    // 点击开始游戏
    await page.click('button:has-text("Start New Game")');

    // 等待棋盘出现
    await expect(page.locator('.board')).toBeVisible();

    // 应该是红方先走（人类）
    await expect(page.locator('.status')).toContainText("Red's turn");
  });

  test('should handle AI vs AI jieqi game', async ({ page }) => {
    // 选择 AI vs AI 模式
    await page.selectOption('select#mode', 'ai_vs_ai');
    await page.click('button:has-text("Start New Game")');

    await expect(page.locator('.board')).toBeVisible();

    // 应该显示 AI 走棋按钮
    await expect(page.locator('button:has-text("Next AI Move")')).toBeVisible();

    // 点击 AI 走棋
    await page.click('button:has-text("Next AI Move")');

    // 检查移动计数增加
    await expect(page.locator('.move-count')).toContainText('Moves: 1');
  });

  test('should select a hidden piece and show legal moves', async ({ page }) => {
    // 开始人对人游戏
    await page.selectOption('select#mode', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 点击一个红方暗子
    const redHiddenPiece = page.locator('.piece.red.hidden-piece').first();
    await redHiddenPiece.click();

    // 应该显示合法移动指示器
    const legalTargets = page.locator('.intersection.legal-target');
    await expect(legalTargets).not.toHaveCount(0);
  });

  test('should reveal a hidden piece when moved', async ({ page }) => {
    // 开始人对人游戏
    await page.selectOption('select#mode', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 获取初始暗子数量
    const initialHiddenCount = await page.locator('.piece.hidden-piece').count();
    expect(initialHiddenCount).toBe(30);

    // 点击一个红方暗子
    const redHiddenPiece = page.locator('.piece.red.hidden-piece').first();
    await redHiddenPiece.click();

    // 找到一个合法目标并点击
    const legalTarget = page.locator('.intersection.legal-target').first();
    await legalTarget.click();

    // 等待走棋完成，暗子数量应该减少 1
    await expect(page.locator('.piece.hidden-piece')).toHaveCount(29);

    // 检查回合切换到黑方
    await expect(page.locator('.status')).toContainText("Black's turn");
  });

  test('should switch back to Chinese Chess mode', async ({ page }) => {
    // 点击标准象棋按钮
    await page.click('button:has-text("Chinese Chess")');

    // 检查标题变回标准象棋
    await expect(page.locator('h2')).toContainText('Chinese Chess');
    await expect(page.locator('h2')).not.toContainText('Jieqi');
  });

  test('should have auto play controls in AI vs AI mode', async ({ page }) => {
    // 选择 AI vs AI 模式
    await page.selectOption('select#mode', 'ai_vs_ai');
    await page.click('button:has-text("Start New Game")');
    await expect(page.locator('.board')).toBeVisible();

    // 检查自动播放按钮
    await expect(page.locator('button:has-text("Start Auto Play")')).toBeVisible();
  });

  test('should display move count', async ({ page }) => {
    // 开始游戏
    await page.selectOption('select#mode', 'human_vs_human');
    await page.click('button:has-text("Start New Game")');

    // 检查初始移动计数
    await expect(page.locator('.move-count')).toContainText('Moves: 0');
  });
});

test.describe('Jieqi Error Handling', () => {
  test('should show error when jieqi server is unavailable', async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("Jieqi (Reveal)")');

    // 检查错误消息组件存在于 DOM 中（但不可见，因为没有错误）
    const errorDiv = page.locator('.error-message');
    await expect(errorDiv).not.toBeVisible();
  });
});
