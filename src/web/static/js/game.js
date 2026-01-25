/**
 * 华夏篮球联赛教练模拟器 - 前端JavaScript
 * Requirements: 6.1-6.10
 */

const GameApp = {
    // 应用状态
    state: {
        isGameStarted: false,
        currentPage: 'menu',
        selectedTeamId: null,
        selectedSaveSlot: null,
        gameState: null,
        selectedTrainingProgram: null,
        selectedTradePlayers: { my: [], other: [] },
        currentLeaderboardStat: 'points',
        leaderboardMode: 'regular',  // 'regular' 或 'playoff'
        leaderboardPlayerFilter: 'all',  // 'all' 或 'domestic'（本土球员）
        rosterMode: 'regular',  // 'regular', 'playoff' 或 'total'
        rosterTeamList: [],  // 所有球队列表
        rosterTeamIndex: 0   // 当前查看的球队索引
    },

    // API基础URL
    apiBase: '/api',

    // ============================================
    // 初始化
    // ============================================
    init() {
        this.bindEvents();
        this.checkGameState();
    },

    bindEvents() {
        // 主菜单按钮
        document.getElementById('btn-new-game')?.addEventListener('click', () => this.showTeamSelect());
        document.getElementById('btn-load-game')?.addEventListener('click', () => this.showLoadGame());
        document.getElementById('btn-about')?.addEventListener('click', () => this.showAbout());
        
        // 球队选择
        document.getElementById('btn-back-menu')?.addEventListener('click', () => this.showPage('menu'));
        document.getElementById('btn-start-game')?.addEventListener('click', () => this.startNewGame());
        
        // 存档选择
        document.getElementById('btn-back-menu-load')?.addEventListener('click', () => this.showPage('menu'));
        document.getElementById('btn-load-selected')?.addEventListener('click', () => this.loadSelectedGame());

        // 模态框关闭
        document.getElementById('modal-close')?.addEventListener('click', () => this.closeModal());
        document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
            if (e.target.id === 'modal-overlay') this.closeModal();
        });

        // 导航链接
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                if (page === 'home') {
                    window.location.href = '/';
                } else if (page && this.state.isGameStarted) {
                    this.showPage(page);
                }
            });
        });

        // 交易球队选择
        document.getElementById('trade-team-select')?.addEventListener('change', () => this.loadTradeTeamRoster());

        // 关闭页面时提醒保存
        window.addEventListener('beforeunload', (e) => {
            // 只有游戏已开始时才提醒
            if (this.state.isGameStarted) {
                e.preventDefault();
                // 现代浏览器会显示默认提示，自定义消息可能被忽略
                e.returnValue = '游戏进度可能未保存，确定要离开吗？';
                return e.returnValue;
            }
        });
    },

    async checkGameState() {
        try {
            const response = await this.apiGet('/game/state');
            if (response.success) {
                this.state.isGameStarted = true;
                this.state.gameState = response.data;
                this.updateNavigation(true);
            }
        } catch (e) {
            // 游戏未开始，保持在主菜单
        }
    },

    // ============================================
    // API调用方法
    // ============================================
    async apiGet(endpoint) {
        this.showLoading();
        try {
            const response = await fetch(this.apiBase + endpoint);
            const data = await response.json();
            this.hideLoading();
            return data;
        } catch (error) {
            this.hideLoading();
            this.showToast('网络错误: ' + error.message, 'error');
            throw error;
        }
    },

    async apiPost(endpoint, body = {}, options = {}) {
        const { skipLoading = false } = options;
        if (!skipLoading) {
            this.showLoading();
        }
        try {
            const response = await fetch(this.apiBase + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await response.json();
            if (!skipLoading) {
                this.hideLoading();
            }
            return data;
        } catch (error) {
            if (!skipLoading) {
                this.hideLoading();
            }
            this.showToast('网络错误: ' + error.message, 'error');
            throw error;
        }
    },

    // ============================================
    // UI辅助方法
    // ============================================
    showLoading(text = '加载中...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = overlay?.querySelector('.loading-text');
        if (loadingText) loadingText.textContent = text;
        if (overlay) overlay.style.display = 'flex';
    },

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.style.display = 'none';
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        
        setTimeout(() => toast.remove(), 3000);
    },

    showModal(title, content, footer = '') {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-body').innerHTML = content;
        document.getElementById('modal-footer').innerHTML = footer;
        document.getElementById('modal-overlay').style.display = 'flex';
    },

    closeModal() {
        document.getElementById('modal-overlay').style.display = 'none';
    },


    // ============================================
    // 页面导航
    // ============================================
    showPage(page) {
        this.state.currentPage = page;
        
        // 隐藏所有页面内容
        document.querySelectorAll('[id$="-page"], .menu-container').forEach(el => {
            el.classList.add('hidden');
        });
        
        // 显示对应页面
        switch (page) {
            case 'menu':
                document.getElementById('main-menu')?.classList.remove('hidden');
                break;
            case 'team-select':
                document.getElementById('team-select-page')?.classList.remove('hidden');
                this.loadTeams();
                break;
            case 'load-game':
                document.getElementById('load-game-page')?.classList.remove('hidden');
                this.loadSaves();
                break;
            case 'dashboard':
                document.getElementById('dashboard-page')?.classList.remove('hidden');
                this.loadDashboard();
                break;
            case 'roster':
                document.getElementById('roster-page')?.classList.remove('hidden');
                this.loadRoster();
                break;
            case 'training':
                document.getElementById('training-page')?.classList.remove('hidden');
                this.loadTraining();
                break;
            case 'trade':
                document.getElementById('trade-page')?.classList.remove('hidden');
                this.loadTrade();
                break;
            case 'match':
                document.getElementById('match-page')?.classList.remove('hidden');
                this.loadMatch();
                break;
            case 'leaderboard':
                document.getElementById('leaderboard-page')?.classList.remove('hidden');
                this.loadLeaderboard();
                break;
            case 'daily-games':
                document.getElementById('daily-games-page')?.classList.remove('hidden');
                this.loadDailyGamesPage();
                break;
            case 'playoff-round-games':
                document.getElementById('daily-games-page')?.classList.remove('hidden');
                this.loadPlayoffRoundGamesPage();
                break;
            case 'schedule':
                document.getElementById('schedule-page')?.classList.remove('hidden');
                this.loadSchedule();
                break;
        }
        
        // 更新导航高亮
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.dataset.page === page) link.classList.add('active');
        });
    },

    updateNavigation(gameStarted) {
        const navLinks = ['dashboard', 'roster', 'schedule', 'leaderboard', 'training', 'trade'];
        navLinks.forEach(link => {
            const el = document.getElementById(`nav-${link}`);
            if (el) el.style.display = gameStarted ? 'inline-block' : 'none';
        });
        
        const navStatus = document.getElementById('nav-status');
        if (navStatus) navStatus.style.display = gameStarted ? 'flex' : 'none';
        
        if (gameStarted && this.state.gameState) {
            document.getElementById('status-date').textContent = this.state.gameState.current_date;
            document.getElementById('status-team').textContent = this.state.gameState.player_team?.name || '';
        }
    },

    // ============================================
    // 主菜单功能
    // ============================================
    showTeamSelect() {
        this.showPage('team-select');
    },

    showLoadGame() {
        this.showPage('load-game');
    },

    showAbout() {
        const content = document.getElementById('about-content')?.innerHTML || '';
        this.showModal('关于游戏', content);
    },

    // ============================================
    // 球队选择
    // ============================================
    async loadTeams() {
        const response = await this.apiGet('/teams');
        if (!response.success) {
            this.showToast(response.error?.message || '加载球队失败', 'error');
            return;
        }
        
        const grid = document.getElementById('team-grid');
        if (!grid) return;
        
        grid.innerHTML = response.data.map(team => `
            <div class="card team-card" data-team-id="${team.id}" onclick="GameApp.selectTeam('${team.id}')">
                <div class="card-body">
                    <div class="team-info">
                        <div class="team-logo">🏀</div>
                        <div>
                            <div class="team-name">${team.name}</div>
                            <div class="team-city">${team.city}</div>
                        </div>
                    </div>
                    <div class="team-stats">
                        <div class="team-stat">
                            <div class="team-stat-value">${team.roster_size}</div>
                            <div class="team-stat-label">球员数</div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    selectTeam(teamId) {
        this.state.selectedTeamId = teamId;
        
        document.querySelectorAll('.team-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.teamId === teamId);
        });
        
        const btn = document.getElementById('btn-start-game') || document.getElementById('btn-confirm-team');
        if (btn) btn.disabled = false;
    },

    async startNewGame() {
        if (!this.state.selectedTeamId) {
            this.showToast('请先选择一支球队', 'warning');
            return;
        }
        
        const response = await this.apiPost('/game/new', { team_id: this.state.selectedTeamId });
        if (response.success) {
            this.state.isGameStarted = true;
            this.showToast('游戏创建成功！', 'success');
            await this.refreshGameState();
            this.updateNavigation(true);
            this.showPage('dashboard');
        } else {
            this.showToast(response.error?.message || '创建游戏失败', 'error');
        }
    },

    // ============================================
    // 存档管理
    // ============================================
    async loadSaves() {
        const response = await this.apiGet('/saves');
        if (!response.success) return;
        
        const container = document.getElementById('save-slots');
        if (!container) return;
        
        // 创建10个存档槽位
        let html = '';
        for (let i = 1; i <= 10; i++) {
            const save = response.data.find(s => s.slot === i);
            if (save) {
                html += `
                    <div class="save-slot" data-slot="${i}" onclick="GameApp.selectSaveSlot(${i})">
                        <div class="save-slot-number">存档 ${i}</div>
                        <div class="save-slot-info">${save.team_name} - ${save.phase_name}</div>
                        <div class="save-slot-time">${save.save_time}</div>
                        <button class="btn btn-sm btn-danger save-delete-btn" onclick="event.stopPropagation(); GameApp.confirmDeleteSave(${i})">🗑️ 删除</button>
                    </div>
                `;
            } else {
                html += `
                    <div class="save-slot" data-slot="${i}" onclick="GameApp.selectSaveSlot(${i})">
                        <div class="save-slot-number">存档 ${i}</div>
                        <div class="save-slot-empty">空</div>
                    </div>
                `;
            }
        }
        container.innerHTML = html;
    },

    /**
     * 确认删除存档
     */
    confirmDeleteSave(slot) {
        const content = `
            <p>确定要删除存档 ${slot} 吗？</p>
            <p class="text-danger">此操作不可撤销！</p>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="GameApp.closeModal()">取消</button>
            <button class="btn btn-danger" onclick="GameApp.deleteSave(${slot})">确认删除</button>
        `;
        this.showModal('删除存档', content, footer);
    },

    /**
     * 删除存档
     */
    async deleteSave(slot) {
        this.closeModal();
        
        try {
            const response = await fetch(`${this.apiBase}/saves/${slot}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`存档 ${slot} 已删除`, 'success');
                // 刷新存档列表
                await this.loadSaves();
            } else {
                this.showToast(data.error?.message || '删除存档失败', 'error');
            }
        } catch (error) {
            this.showToast('删除存档出错: ' + error.message, 'error');
        }
    },

    selectSaveSlot(slot) {
        this.state.selectedSaveSlot = slot;
        
        document.querySelectorAll('.save-slot').forEach(el => {
            el.classList.toggle('selected', parseInt(el.dataset.slot) === slot);
        });
        
        const btn = document.getElementById('btn-load-selected');
        if (btn) btn.disabled = false;
    },

    async loadSelectedGame() {
        if (!this.state.selectedSaveSlot) {
            this.showToast('请先选择一个存档', 'warning');
            return;
        }
        
        const response = await this.apiPost('/game/load', { slot: this.state.selectedSaveSlot });
        if (response.success) {
            this.state.isGameStarted = true;
            this.showToast('存档加载成功！', 'success');
            await this.refreshGameState();
            this.updateNavigation(true);
            this.showPage('dashboard');
        } else {
            this.showToast(response.error?.message || '加载存档失败', 'error');
        }
    },

    async saveGame() {
        const content = `
            <p>选择存档槽位：</p>
            <div class="save-slots" id="save-modal-slots" style="margin-top: 15px;"></div>
        `;
        const footer = `
            <button class="btn btn-secondary" onclick="GameApp.closeModal()">取消</button>
            <button class="btn btn-primary" id="btn-confirm-save" onclick="GameApp.confirmSave()" disabled>保存</button>
        `;
        this.showModal('保存游戏', content, footer);
        
        // 加载存档列表
        const response = await this.apiGet('/saves');
        const container = document.getElementById('save-modal-slots');
        if (!container) return;
        
        let html = '';
        for (let i = 1; i <= 10; i++) {
            const save = response.data?.find(s => s.slot === i);
            html += `
                <div class="save-slot" data-slot="${i}" onclick="GameApp.selectModalSaveSlot(${i})" style="margin-bottom: 10px;">
                    <div class="save-slot-number">存档 ${i}</div>
                    ${save ? `<div class="save-slot-info">${save.team_name}</div><div class="save-slot-time">${save.save_time}</div>` : '<div class="save-slot-empty">空</div>'}
                </div>
            `;
        }
        container.innerHTML = html;
    },

    selectModalSaveSlot(slot) {
        this.state.selectedSaveSlot = slot;
        document.querySelectorAll('#save-modal-slots .save-slot').forEach(el => {
            el.classList.toggle('selected', parseInt(el.dataset.slot) === slot);
        });
        document.getElementById('btn-confirm-save').disabled = false;
    },

    async confirmSave() {
        const response = await this.apiPost('/game/save', { slot: this.state.selectedSaveSlot });
        this.closeModal();
        if (response.success) {
            this.showToast('游戏保存成功！', 'success');
        } else {
            this.showToast(response.error?.message || '保存失败', 'error');
        }
    },

    async exportPlayers() {
        const response = await this.apiGet('/game/export-players');
        if (!response.success) {
            this.showToast(response.error?.message || '导出失败', 'error');
            return;
        }
        
        // 创建并下载JSON文件
        const jsonStr = JSON.stringify(response.data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'players.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('球员名单已导出！', 'success');
    },


    // ============================================
    // Dashboard
    // ============================================
    async loadDashboard() {
        await this.refreshGameState();
        const state = this.state.gameState;
        if (!state) return;
        
        // 更新日期和状态
        document.getElementById('current-date').textContent = state.current_date;
        document.getElementById('day-type').textContent = this.getDayTypeText(state.day_type);
        
        // 更新比赛日/训练日状态显示 (Requirements 5.1, 7.1)
        this.updateDayStatusBadge(state);
        
        // 更新球队信息
        document.getElementById('team-name').textContent = state.player_team?.name || '--';
        document.getElementById('team-rank').textContent = `第${state.player_team?.rank || '--'}名`;
        document.getElementById('team-record').textContent = `${state.player_team?.wins || 0}-${state.player_team?.losses || 0}`;
        document.getElementById('team-win-pct').textContent = (state.player_team?.win_pct * 100 || 0).toFixed(1) + '%';
        document.getElementById('team-budget-display').textContent = state.player_team?.budget || 0;
        
        // 根据 dashboard_action 动态显示按钮 (Requirements 5.1, 5.2, 5.4, 7.1)
        this.updateDashboardButtons(state);
        
        // 根据季后赛状态切换显示内容 (Requirements 2.1, 4.1)
        await this.updateDashboardForPlayoffPhase(state);
        
        // 今日比赛卡片 (仅常规赛显示)
        if (!state.is_playoff_phase) {
            this.updateTodayGameCard(state);
        } else {
            document.getElementById('today-game-card')?.classList.add('hidden');
        }
        
        // 训练按钮状态 - 使用后端返回的 can_train 字段
        const trainingBtn = document.getElementById('btn-training');
        if (trainingBtn) {
            const cannotTrain = state.can_train === false;
            trainingBtn.disabled = cannotTrain;
            if (cannotTrain) {
                trainingBtn.title = '今天有比赛，无法训练';
            } else {
                trainingBtn.title = '';
            }
        }
        
        // 加载排名 (仅常规赛)
        if (!state.is_playoff_phase) {
            await this.loadStandingsPreview();
        }
        
        // 加载近期赛程 (仅常规赛)
        if (!state.is_playoff_phase) {
            await this.loadUpcomingGames();
        }
    },

    /**
     * 根据季后赛状态更新Dashboard显示 (Requirements 2.1, 4.1)
     */
    async updateDashboardForPlayoffPhase(state) {
        const standingsCard = document.getElementById('standings-card');
        const playoffBracketCard = document.getElementById('playoff-bracket-card');
        const upcomingGamesCard = document.getElementById('upcoming-games-card');
        const playoffStatusCard = document.getElementById('playoff-status-card');
        
        if (state.is_playoff_phase) {
            // 季后赛阶段：隐藏常规赛排名，显示季后赛对阵图
            if (standingsCard) standingsCard.style.display = 'none';
            if (playoffBracketCard) playoffBracketCard.style.display = 'block';
            if (upcomingGamesCard) upcomingGamesCard.style.display = 'none';
            if (playoffStatusCard) playoffStatusCard.style.display = 'block';
            
            // 加载并渲染季后赛对阵图
            const bracketData = await this.loadPlayoffBracket();
            if (bracketData) {
                this.renderPlayoffBracket(bracketData);
            }
            
            // 更新季后赛状态卡片
            this.updatePlayoffStatusCard(state);
            
            // 更新日期状态徽章为季后赛状态
            this.updatePlayoffDayStatusBadge(state);
        } else {
            // 常规赛阶段：显示常规赛排名，隐藏季后赛对阵图
            if (standingsCard) standingsCard.style.display = 'block';
            if (playoffBracketCard) playoffBracketCard.style.display = 'none';
            if (upcomingGamesCard) upcomingGamesCard.style.display = 'block';
            if (playoffStatusCard) playoffStatusCard.style.display = 'none';
        }
    },

    /**
     * 更新季后赛状态卡片
     */
    updatePlayoffStatusCard(state) {
        const container = document.getElementById('playoff-status-content');
        if (!container) return;
        
        const playoffStatus = state.player_team_playoff_status || {};
        
        let statusHtml = '';
        
        if (playoffStatus.is_champion) {
            statusHtml = `
                <div class="playoff-status-item champion">
                    <div class="status-icon">🏆</div>
                    <div class="status-text">恭喜！您的球队获得了总冠军！</div>
                </div>
            `;
        } else if (playoffStatus.is_eliminated) {
            statusHtml = `
                <div class="playoff-status-item eliminated">
                    <div class="status-icon">😢</div>
                    <div class="status-text">您的球队已被淘汰</div>
                    <div class="status-hint">您可以继续观看剩余的季后赛比赛</div>
                </div>
            `;
        } else if (playoffStatus.is_in_playoffs) {
            const seriesScore = playoffStatus.series_score || '0-0';
            const gamePlayedHint = playoffStatus.game_played_this_round 
                ? '<div class="status-hint" style="color: var(--warning-color);">请先点击"推进季后赛"让其他球队比赛</div>'
                : '<div class="status-hint">点击"季后赛比赛"进行下一场比赛</div>';
            statusHtml = `
                <div class="playoff-status-item active">
                    <div class="status-icon">🏀</div>
                    <div class="status-text">您的球队正在季后赛中</div>
                    <div class="status-series">
                        当前系列赛比分: <strong>${seriesScore}</strong>
                    </div>
                    ${gamePlayedHint}
                </div>
            `;
        } else {
            statusHtml = `
                <div class="playoff-status-item waiting">
                    <div class="status-icon">⏳</div>
                    <div class="status-text">等待季后赛开始</div>
                </div>
            `;
        }
        
        // 添加查看比赛数据按钮
        statusHtml += `
            <div style="margin-top: 15px; text-align: center;">
                <button class="btn btn-outline" onclick="GameApp.showPage('playoff-round-games')">
                    📊 查看比赛数据
                </button>
            </div>
        `;
        
        container.innerHTML = statusHtml;
    },

    /**
     * 更新季后赛阶段的日期状态徽章
     */
    updatePlayoffDayStatusBadge(state) {
        const badge = document.getElementById('day-status-badge');
        const statusText = document.getElementById('day-status-text');
        
        if (!badge || !statusText) return;
        
        const playoffStatus = state.player_team_playoff_status || {};
        
        badge.style.display = 'inline-block';
        
        if (playoffStatus.is_champion) {
            statusText.textContent = '🏆 总冠军！';
            badge.className = 'day-status-badge status-champion';
        } else if (playoffStatus.is_eliminated) {
            statusText.textContent = '📺 观看季后赛';
            badge.className = 'day-status-badge status-eliminated';
        } else if (playoffStatus.current_series_id) {
            // 根据是否已打过一场显示不同状态
            if (playoffStatus.game_played_this_round) {
                statusText.textContent = '⏭️ 等待推进';
                badge.className = 'day-status-badge status-training';
            } else {
                statusText.textContent = '🏀 季后赛进行中';
                badge.className = 'day-status-badge status-match-day';
            }
        } else {
            statusText.textContent = '⏳ 等待下一轮';
            badge.className = 'day-status-badge status-training';
        }
    },

    /**
     * 更新比赛日/训练日状态徽章 (Requirements 5.1, 7.1)
     */
    updateDayStatusBadge(state) {
        const badge = document.getElementById('day-status-badge');
        const statusText = document.getElementById('day-status-text');
        
        if (!badge || !statusText) return;
        
        if (state.has_player_match_today) {
            badge.style.display = 'inline-block';
            if (state.player_match_completed_today) {
                statusText.textContent = '✅ 今日比赛已完成';
                badge.className = 'day-status-badge status-completed';
            } else {
                statusText.textContent = '🏀 今日有比赛';
                badge.className = 'day-status-badge status-match-day';
            }
        } else if (state.is_match_day) {
            badge.style.display = 'inline-block';
            statusText.textContent = '📺 今日有其他比赛';
            badge.className = 'day-status-badge status-other-match';
        } else {
            badge.style.display = 'inline-block';
            statusText.textContent = '🏋️ 训练日';
            badge.className = 'day-status-badge status-training';
        }
    },

    /**
     * 根据 dashboard_action 动态显示按钮 (Requirements 5.1, 5.2, 5.4, 7.1)
     */
    updateDashboardButtons(state) {
        const goToMatchBtn = document.getElementById('btn-go-to-match');
        const advanceDayBtn = document.getElementById('btn-advance-day');
        const enterPlayoffsBtn = document.getElementById('btn-enter-playoffs');
        
        if (!goToMatchBtn || !advanceDayBtn) return;
        
        // 调试日志：检查季后赛入口条件
        console.log('updateDashboardButtons called:', {
            can_enter_playoffs: state.can_enter_playoffs,
            is_playoff_phase: state.is_playoff_phase,
            enterPlayoffsBtn_exists: !!enterPlayoffsBtn,
            playoff_dashboard_action: state.playoff_dashboard_action
        });
        const action = state.dashboard_action;
        
        // 处理季后赛入口按钮显示 (Requirements 1.1, 1.2)
        if (enterPlayoffsBtn) {
            if (state.can_enter_playoffs && !state.is_playoff_phase) {
                console.log('Showing enter playoffs button');
                enterPlayoffsBtn.style.display = 'inline-block';
            } else {
                console.log('Hiding enter playoffs button');
                enterPlayoffsBtn.style.display = 'none';
            }
        } else {
            console.log('WARNING: enterPlayoffsBtn not found!');
        }
        
        // 季后赛阶段的按钮逻辑
        if (state.is_playoff_phase) {
            // 季后赛阶段 - 使用后端返回的 playoff_dashboard_action 来决定按钮
            const playoffStatus = state.player_team_playoff_status || {};
            const playoffAction = state.playoff_dashboard_action;
            
            if (playoffAction === 'champion' || playoffStatus.is_champion) {
                // 玩家获得冠军
                goToMatchBtn.style.display = 'none';
                advanceDayBtn.style.display = 'inline-block';
                advanceDayBtn.textContent = '🏆 查看季后赛';
                advanceDayBtn.onclick = () => GameApp.showPlayoffBracket();
            } else if (playoffAction === 'view_playoffs' || playoffStatus.is_eliminated) {
                // 玩家已淘汰
                goToMatchBtn.style.display = 'none';
                advanceDayBtn.style.display = 'inline-block';
                advanceDayBtn.textContent = '📺 观看季后赛';
                advanceDayBtn.onclick = () => GameApp.advancePlayoffs();
            } else if (playoffAction === 'go_to_match') {
                // 玩家可以进行比赛
                goToMatchBtn.style.display = 'inline-block';
                goToMatchBtn.textContent = '🏀 季后赛比赛';
                goToMatchBtn.onclick = () => GameApp.goToPlayoffMatch();
                advanceDayBtn.style.display = 'none';
            } else if (playoffAction === 'advance_series') {
                // 玩家已打过一场，需要推进AI系列赛
                goToMatchBtn.style.display = 'none';
                advanceDayBtn.style.display = 'inline-block';
                advanceDayBtn.textContent = '⏭️ 推进季后赛';
                advanceDayBtn.onclick = () => GameApp.advancePlayoffs();
            } else {
                // 默认：等待下一轮
                goToMatchBtn.style.display = 'none';
                advanceDayBtn.style.display = 'inline-block';
                advanceDayBtn.textContent = '⏭️ 推进季后赛';
                advanceDayBtn.onclick = () => GameApp.advancePlayoffs();
            }
        } else if (action === 'go_to_match') {
            // 常规赛：显示"前往比赛"按钮，隐藏"推进日期"按钮
            goToMatchBtn.style.display = 'inline-block';
            goToMatchBtn.textContent = '🏀 前往比赛';
            goToMatchBtn.onclick = () => GameApp.goToMatch();
            advanceDayBtn.style.display = 'none';
        } else {
            // 常规赛：显示"推进日期"按钮，隐藏"前往比赛"按钮
            goToMatchBtn.style.display = 'none';
            advanceDayBtn.style.display = 'inline-block';
            advanceDayBtn.textContent = '⏭️ 推进日期';
            advanceDayBtn.onclick = () => GameApp.advanceDay();
        }
    },

    /**
     * 更新今日比赛卡片 (Requirements 5.1, 7.1)
     */
    updateTodayGameCard(state) {
        const todayGameCard = document.getElementById('today-game-card');
        const todayGameStatus = document.getElementById('today-game-status');
        const todayGameAction = document.getElementById('today-game-action');
        
        if (state.has_player_match_today && state.today_game) {
            todayGameCard?.classList.remove('hidden');
            document.getElementById('today-home-team').textContent = 
                state.today_game.is_home ? state.player_team?.name : state.today_game.opponent_name;
            document.getElementById('today-away-team').textContent = 
                state.today_game.is_home ? state.today_game.opponent_name : state.player_team?.name;
            
            // 更新比赛状态
            if (todayGameStatus) {
                if (state.player_match_completed_today) {
                    todayGameStatus.innerHTML = '<span class="text-success">✅ 比赛已完成</span>';
                } else {
                    todayGameStatus.innerHTML = '<span class="text-warning">⏳ 等待比赛</span>';
                }
            }
            
            // 更新操作按钮
            if (todayGameAction) {
                if (state.player_match_completed_today) {
                    todayGameAction.innerHTML = `
                        <button class="btn btn-lg" style="background: white; color: var(--success-color);" 
                                onclick="GameApp.showPage('daily-games')">
                            📊 查看比赛数据
                        </button>
                    `;
                } else {
                    todayGameAction.innerHTML = `
                        <button class="btn btn-lg" style="background: white; color: var(--primary-color);" 
                                onclick="GameApp.goToMatch()">
                            🏀 开始比赛
                        </button>
                    `;
                }
            }
        } else {
            todayGameCard?.classList.add('hidden');
        }
    },

    getDayTypeText(dayType) {
        const types = {
            'match_day': '🏀 比赛日',
            'rest_day': '😴 休息日',
            'training_day': '🏋️ 训练日'
        };
        return types[dayType] || dayType;
    },

    async loadStandingsPreview() {
        const response = await this.apiGet('/standings');
        if (!response.success) return;
        
        const tbody = document.getElementById('standings-body');
        if (!tbody) return;
        
        // 只显示前8名
        tbody.innerHTML = response.data.slice(0, 8).map(team => `
            <tr class="${team.team_id === this.state.gameState?.player_team?.id ? 'text-primary' : ''}">
                <td>${team.rank}</td>
                <td>${team.team_name}</td>
                <td>${team.wins}</td>
                <td>${team.losses}</td>
                <td>${(team.win_pct * 100).toFixed(1)}%</td>
            </tr>
        `).join('');
    },

    async loadUpcomingGames() {
        const teamId = this.state.gameState?.player_team?.id;
        if (!teamId) return;
        
        const response = await this.apiGet(`/schedule?team_id=${teamId}&played=false&limit=5`);
        if (!response.success) return;
        
        const container = document.getElementById('upcoming-games');
        if (!container) return;
        
        if (response.data.schedule.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">暂无upcoming比赛</p>';
            return;
        }
        
        container.innerHTML = response.data.schedule.map(game => {
            const isHome = game.home_team_id === teamId;
            const opponent = isHome ? game.away_team_name : game.home_team_name;
            return `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between;">
                        <span>${game.date}</span>
                        <span>${isHome ? '主场' : '客场'} vs ${opponent}</span>
                    </div>
                </div>
            `;
        }).join('');
    },

    async refreshGameState() {
        const response = await this.apiGet('/game/state');
        if (response.success) {
            this.state.gameState = response.data;
            this.updateNavigation(true);
        }
    },

    /**
     * 前往比赛页面 (Requirements 5.2, 5.4, 7.1)
     * 当玩家球队今天有比赛且未完成时调用
     */
    goToMatch() {
        this.showPage('match');
    },

    /**
     * 推进日期 (Requirements 1.1, 1.5, 5.4, 5.5, 7.1)
     * 调用 /api/advance-day-only 端点
     * - 仅推进日期到下一天，不模拟下一天的比赛
     * - 如果当前日期有未模拟的AI比赛，先模拟这些比赛
     */
    async advanceDay() {
        const state = this.state.gameState;
        
        // 检查是否需要先完成玩家比赛 (Requirements 2.1, 2.3)
        if (state?.has_player_match_today && !state?.player_match_completed_today) {
            this.showToast('请先完成今日比赛', 'warning');
            return;
        }
        
        // 显示加载状态
        this.showLoading('推进日期中...');
        
        try {
            // 调用 advance-day-only API (Requirements 1.1, 1.5)
            const response = await this.apiPost('/advance-day-only', {}, { skipLoading: true });
            
            this.hideLoading();
            
            if (response.success) {
                const data = response.data;
                let message = `日期推进到 ${data.new_date}`;
                
                // 显示AI比赛模拟结果数量
                if (data.ai_matches_simulated && data.ai_matches_simulated.length > 0) {
                    message += `，模拟了 ${data.ai_matches_simulated.length} 场其他比赛`;
                }
                
                this.showToast(message, 'success');
                
                // 显示伤病信息
                if (data.new_injuries && data.new_injuries.length > 0) {
                    const injuryNames = data.new_injuries.map(i => i.player_name).join('、');
                    this.showToast(`⚠️ 伤病: ${injuryNames}`, 'warning');
                }
                
                // 显示恢复信息
                if (data.recovered_players && data.recovered_players.length > 0) {
                    const recoveredNames = data.recovered_players.map(p => p.player_name).join('、');
                    this.showToast(`✅ 恢复: ${recoveredNames}`, 'success');
                }
                
                // 刷新Dashboard显示 (Requirements 1.5)
                await this.loadDashboard();
                
                // 如果当前在外援市场页面，刷新外援市场数据以更新剩余天数
                const foreignMarketPanel = document.getElementById('foreign-market-panel');
                if (foreignMarketPanel && !foreignMarketPanel.classList.contains('hidden')) {
                    await this.loadForeignMarketInfo();
                }
            } else {
                this.showToast(response.error?.message || '推进日期失败', 'error');
            }
        } catch (error) {
            this.hideLoading();
            this.showToast('推进日期出错: ' + error.message, 'error');
        }
    },

    // ============================================
    // 季后赛系统 (Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4)
    // ============================================
    
    /**
     * 进入季后赛 (Requirements 1.1, 1.2, 1.3)
     * 调用 /api/playoff/init 端点初始化季后赛
     */
    async enterPlayoffs() {
        this.showLoading('初始化季后赛...');
        
        try {
            const response = await this.apiPost('/playoff/init', {}, { skipLoading: true });
            
            this.hideLoading();
            
            if (response.success) {
                this.showToast('🏆 季后赛开始！', 'success');
                
                // 显示AI能力值调整信息
                if (response.data.ai_adjustments) {
                    const adjustCount = Object.keys(response.data.ai_adjustments).length;
                    if (adjustCount > 0) {
                        this.showToast(`AI球员能力值已调整 (${adjustCount}名球员)`, 'info');
                    }
                }
                
                // 刷新游戏状态并显示季后赛对阵图
                await this.refreshGameState();
                await this.loadDashboard();
            } else {
                this.showToast(response.error?.message || '初始化季后赛失败', 'error');
            }
        } catch (error) {
            this.hideLoading();
            this.showToast('初始化季后赛出错: ' + error.message, 'error');
        }
    },

    /**
     * 加载季后赛对阵图数据 (Requirements 2.1, 2.2, 2.3, 2.4)
     */
    async loadPlayoffBracket() {
        try {
            const response = await this.apiGet('/playoff/bracket');
            
            if (response.success) {
                return response.data;
            } else {
                console.error('Failed to load playoff bracket:', response.error);
                return null;
            }
        } catch (error) {
            console.error('Error loading playoff bracket:', error);
            return null;
        }
    },

    /**
     * 渲染季后赛对阵图 (Requirements 2.1, 2.2, 2.3, 2.4)
     * @param {Object} bracketData - 季后赛对阵图数据
     */
    renderPlayoffBracket(bracketData) {
        const container = document.getElementById('playoff-bracket');
        if (!container) return;
        
        if (!bracketData || !bracketData.is_playoff_phase) {
            container.innerHTML = '<p class="text-muted text-center">季后赛尚未开始</p>';
            return;
        }
        
        const currentRound = bracketData.current_round || 'play_in';
        const playerTeamId = this.state.gameState?.player_team?.id;
        
        let html = `
            <div class="playoff-bracket-container">
                <div class="playoff-round-indicator">
                    当前轮次: <span class="current-round-name">${this.getRoundDisplayName(currentRound)}</span>
                </div>
        `;
        
        // 渲染附加赛 (Play-In)
        if (bracketData.play_in && bracketData.play_in.length > 0) {
            html += this.renderPlayoffRound('附加赛 (12进8)', bracketData.play_in, playerTeamId, currentRound === 'play_in');
        }
        
        // 渲染四分之一决赛
        if (bracketData.quarter && bracketData.quarter.length > 0) {
            html += this.renderPlayoffRound('四分之一决赛', bracketData.quarter, playerTeamId, currentRound === 'quarter');
        }
        
        // 渲染半决赛
        if (bracketData.semi && bracketData.semi.length > 0) {
            html += this.renderPlayoffRound('半决赛', bracketData.semi, playerTeamId, currentRound === 'semi');
        }
        
        // 渲染总决赛
        if (bracketData.final) {
            const finalSeries = Array.isArray(bracketData.final) ? bracketData.final : [bracketData.final];
            if (finalSeries.length > 0 && finalSeries[0].team1_id) {
                html += this.renderPlayoffRound('总决赛', finalSeries, playerTeamId, currentRound === 'final');
            }
        }
        
        // 显示冠军
        if (bracketData.champion_id) {
            html += `
                <div class="playoff-champion">
                    <div class="champion-trophy">🏆</div>
                    <div class="champion-title">总冠军</div>
                    <div class="champion-team-name">${bracketData.champion_name || '冠军球队'}</div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * 渲染季后赛轮次 (Requirements 2.2, 2.3, 2.4)
     */
    renderPlayoffRound(roundName, series, playerTeamId, isCurrentRound) {
        const roundClass = isCurrentRound ? 'playoff-round current-round' : 'playoff-round';
        
        let html = `
            <div class="${roundClass}">
                <div class="playoff-round-header">
                    <span class="round-name">${roundName}</span>
                    ${isCurrentRound ? '<span class="round-badge active">进行中</span>' : ''}
                </div>
                <div class="playoff-series-list">
        `;
        
        series.forEach(s => {
            if (!s || !s.team1_id) return;
            
            const isPlayerSeries = s.team1_id === playerTeamId || s.team2_id === playerTeamId;
            const seriesClass = isPlayerSeries ? 'playoff-series player-series' : 'playoff-series';
            const isComplete = s.is_complete;
            const winsNeeded = s.round_name === 'play_in' ? 2 : 4;
            
            // 确定胜者
            let team1Class = '';
            let team2Class = '';
            if (isComplete) {
                if (s.winner_id === s.team1_id) {
                    team1Class = 'series-winner';
                    team2Class = 'series-loser';
                } else {
                    team1Class = 'series-loser';
                    team2Class = 'series-winner';
                }
            }
            
            html += `
                <div class="${seriesClass} ${isComplete ? 'series-complete' : ''}">
                    <div class="series-team ${team1Class} ${s.team1_id === playerTeamId ? 'player-team' : ''}">
                        <span class="team-name">${s.team1_name || '待定'}</span>
                        <span class="team-wins">${s.team1_wins}</span>
                    </div>
                    <div class="series-vs">
                        <span class="series-score">${s.team1_wins} - ${s.team2_wins}</span>
                        <span class="series-format">(${winsNeeded}胜制)</span>
                    </div>
                    <div class="series-team ${team2Class} ${s.team2_id === playerTeamId ? 'player-team' : ''}">
                        <span class="team-name">${s.team2_name || '待定'}</span>
                        <span class="team-wins">${s.team2_wins}</span>
                    </div>
                    ${isComplete ? `<div class="series-result">✓ ${s.winner_id === s.team1_id ? s.team1_name : s.team2_name} 晋级</div>` : ''}
                </div>
            `;
        });
        
        html += '</div></div>';
        return html;
    },

    /**
     * 获取轮次显示名称
     */
    getRoundDisplayName(round) {
        const names = {
            'play_in': '附加赛',
            'quarter': '四分之一决赛',
            'semi': '半决赛',
            'final': '总决赛',
            'champion': '已结束'
        };
        return names[round] || round;
    },

    /**
     * 显示季后赛对阵图弹窗
     */
    async showPlayoffBracket() {
        const bracketData = await this.loadPlayoffBracket();
        if (!bracketData) {
            this.showToast('无法加载季后赛对阵图', 'error');
            return;
        }
        
        // 直接生成对阵图HTML内容
        const content = this.generatePlayoffBracketHtml(bracketData);
        
        this.showModal('🏆 季后赛对阵图', `<div id="playoff-bracket-modal">${content}</div>`);
    },

    /**
     * 生成季后赛对阵图HTML（不依赖DOM容器）
     */
    generatePlayoffBracketHtml(bracketData) {
        if (!bracketData || !bracketData.is_playoff_phase) {
            return '<p class="text-muted text-center">季后赛尚未开始</p>';
        }
        
        const currentRound = bracketData.current_round || 'play_in';
        const playerTeamId = this.state.gameState?.player_team?.id;
        
        let html = `
            <div class="playoff-bracket-container">
                <div class="playoff-round-indicator">
                    当前轮次: <span class="current-round-name">${this.getRoundDisplayName(currentRound)}</span>
                </div>
        `;
        
        // 渲染附加赛 (Play-In)
        if (bracketData.play_in && bracketData.play_in.length > 0) {
            html += this.renderPlayoffRound('附加赛 (12进8)', bracketData.play_in, playerTeamId, currentRound === 'play_in');
        }
        
        // 渲染四分之一决赛
        if (bracketData.quarter && bracketData.quarter.length > 0) {
            html += this.renderPlayoffRound('四分之一决赛', bracketData.quarter, playerTeamId, currentRound === 'quarter');
        }
        
        // 渲染半决赛
        if (bracketData.semi && bracketData.semi.length > 0) {
            html += this.renderPlayoffRound('半决赛', bracketData.semi, playerTeamId, currentRound === 'semi');
        }
        
        // 渲染总决赛
        if (bracketData.final) {
            const finalSeries = Array.isArray(bracketData.final) ? bracketData.final : [bracketData.final];
            if (finalSeries.length > 0 && finalSeries[0].team1_id) {
                html += this.renderPlayoffRound('总决赛', finalSeries, playerTeamId, currentRound === 'final');
            }
        }
        
        // 显示冠军
        if (bracketData.champion_id) {
            html += `
                <div class="playoff-champion">
                    <div class="champion-trophy">🏆</div>
                    <div class="champion-title">总冠军</div>
                    <div class="champion-team-name">${bracketData.champion_name || '冠军球队'}</div>
                </div>
            `;
        }
        
        html += '</div>';
        return html;
    },

    /**
     * 前往季后赛比赛
     */
    async goToPlayoffMatch() {
        const state = this.state.gameState;
        const playoffStatus = state?.player_team_playoff_status;
        
        if (!playoffStatus?.current_series_id) {
            this.showToast('当前没有进行中的系列赛', 'warning');
            return;
        }
        
        // 显示加载状态
        this.showLoading('模拟季后赛比赛...');
        
        try {
            const response = await this.apiPost('/playoff/simulate-game', {
                series_id: playoffStatus.current_series_id
            }, { skipLoading: true });
            
            this.hideLoading();
            
            if (response.success) {
                // 显示比赛结果
                await this.showPlayoffMatchResult(response.data);
            } else {
                this.showToast(response.error?.message || '比赛模拟失败', 'error');
            }
        } catch (error) {
            this.hideLoading();
            this.showToast('比赛模拟出错: ' + error.message, 'error');
        }
    },

    /**
     * 显示季后赛比赛结果（含球员统计数据）
     */
    async showPlayoffMatchResult(data) {
        const matchResult = data.match_result;
        const seriesUpdate = data.series_update;
        
        // 隐藏模拟面板
        this.hideLlmSimulatingPanel();
        
        // 判断获胜方
        const homeWinner = matchResult.home_score > matchResult.away_score;
        const awayWinner = matchResult.away_score > matchResult.home_score;
        
        // 构建结果内容
        let content = `
            <div class="playoff-match-result">
                <div class="match-scoreboard" style="margin-bottom: 20px;">
                    <div class="match-teams" style="display: flex; justify-content: center; align-items: center; gap: 30px;">
                        <div class="match-team" style="text-align: center;">
                            <div class="match-team-name" style="font-weight: 600; margin-bottom: 8px;">${matchResult.home_team_name}</div>
                            <div class="match-score" style="font-size: 2.5rem; font-weight: 800; color: ${homeWinner ? 'var(--success-color)' : 'var(--secondary-color)'};">${matchResult.home_score}</div>
                        </div>
                        <div class="match-vs" style="font-size: 1.2rem; color: var(--text-secondary);">VS</div>
                        <div class="match-team" style="text-align: center;">
                            <div class="match-team-name" style="font-weight: 600; margin-bottom: 8px;">${matchResult.away_team_name}</div>
                            <div class="match-score" style="font-size: 2.5rem; font-weight: 800; color: ${awayWinner ? 'var(--success-color)' : 'var(--secondary-color)'};">${matchResult.away_score}</div>
                        </div>
                    </div>
                </div>
                <div class="series-update-info" style="text-align: center; margin-bottom: 20px;">
                    <div class="series-score-update">
                        系列赛比分: <strong>${seriesUpdate.team1_wins} - ${seriesUpdate.team2_wins}</strong>
                    </div>
        `;
        
        if (seriesUpdate.is_complete) {
            const winnerName = seriesUpdate.winner_id === matchResult.home_team_id ? 
                matchResult.home_team_name : matchResult.away_team_name;
            content += `
                    <div class="series-complete-message" style="color: var(--success-color); font-weight: bold; margin-top: 10px;">
                        🎉 ${winnerName} 赢得系列赛！
                    </div>
            `;
        }
        
        content += '</div>';
        
        // 添加球员统计数据
        content += this.renderPlayoffMatchPlayerStats(matchResult);
        
        content += '</div>';
        
        const footer = `
            <button class="btn btn-primary" onclick="GameApp.closeModal(); GameApp.loadDashboard();">
                继续
            </button>
        `;
        
        this.showModal('🏀 季后赛比赛结果', content, footer);
        
        // 刷新游戏状态
        await this.refreshGameState();
    },

    /**
     * 渲染季后赛比赛球员统计数据
     */
    renderPlayoffMatchPlayerStats(matchResult) {
        const playerStats = matchResult.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        return `
            <div class="playoff-player-stats" style="margin-top: 20px;">
                <!-- 主队球员统计 -->
                <div class="team-stats-section" style="margin-bottom: 20px;">
                    <div class="team-stats-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 2px solid var(--primary-color);">
                        <div class="team-stats-title" style="font-weight: 700; color: var(--secondary-color);">
                            🏠 ${matchResult.home_team_name} 球员数据
                        </div>
                        <div class="team-total-score" style="font-weight: 800; color: var(--primary-color);">总分: ${matchResult.home_score}</div>
                    </div>
                    ${this.renderPlayerStatsTable(homeStats, 'home')}
                </div>
                
                <!-- 客队球员统计 -->
                <div class="team-stats-section">
                    <div class="team-stats-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 2px solid var(--primary-color);">
                        <div class="team-stats-title" style="font-weight: 700; color: var(--secondary-color);">
                            ✈️ ${matchResult.away_team_name} 球员数据
                        </div>
                        <div class="team-total-score" style="font-weight: 800; color: var(--primary-color);">总分: ${matchResult.away_score}</div>
                    </div>
                    ${this.renderPlayerStatsTable(awayStats, 'away')}
                </div>
            </div>
        `;
    },

    /**
     * 推进季后赛（模拟AI比赛）
     */
    async advancePlayoffs() {
        this.showLoading('模拟季后赛比赛...');
        
        try {
            // 调用推进季后赛API
            const response = await this.apiPost('/playoff/advance', {}, { skipLoading: true });
            
            this.hideLoading();
            
            if (response.success) {
                const data = response.data;
                
                // 显示模拟结果
                if (data.simulated_games && data.simulated_games.length > 0) {
                    // 显示详细的比赛结果（包含球员统计数据）
                    this.showPlayoffAdvanceResults(data);
                } else {
                    // 没有AI比赛需要模拟，可能是总决赛或所有AI系列赛已结束
                    this.showToast('所有AI系列赛已完成，可以继续您的比赛', 'info');
                    // 刷新Dashboard显示
                    await this.refreshGameState();
                    await this.loadDashboard();
                }
                
                // 检查季后赛是否结束
                if (data.playoffs_complete) {
                    this.showToast('🏆 季后赛已结束！', 'success');
                }
            } else {
                this.showToast(response.error?.message || '推进季后赛失败', 'error');
            }
        } catch (error) {
            this.hideLoading();
            this.showToast('推进季后赛出错: ' + error.message, 'error');
        }
    },

    /**
     * 显示季后赛推进结果（包含球员统计数据）
     */
    showPlayoffAdvanceResults(data) {
        const games = data.simulated_games;
        const seriesUpdates = data.series_updates || [];
        
        let content = `
            <div class="playoff-advance-results">
                <div class="advance-summary" style="text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 1.2rem; color: var(--text-secondary);">
                        模拟了 <strong style="color: var(--primary-color);">${games.length}</strong> 场季后赛比赛
                    </div>
                </div>
        `;
        
        // 为每场比赛生成结果卡片
        for (let i = 0; i < games.length; i++) {
            const game = games[i];
            const seriesUpdate = seriesUpdates[i] || {};
            const homeWinner = game.home_score > game.away_score;
            const awayWinner = game.away_score > game.home_score;
            
            content += `
                <div class="playoff-game-card" style="background: var(--card-bg); border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid var(--border-color);">
                    <div class="game-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span class="series-badge" style="background: var(--primary-color); color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem;">
                            ${this.formatSeriesId(game.series_id)}
                        </span>
                        ${seriesUpdate.is_complete ? '<span style="color: var(--success-color); font-weight: bold;">🎉 系列赛结束</span>' : ''}
                    </div>
                    <div class="game-scoreboard" style="display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 12px;">
                        <div class="team-score" style="text-align: center;">
                            <div style="font-weight: 600; margin-bottom: 4px; color: ${homeWinner ? 'var(--success-color)' : 'var(--text-secondary)'};">${game.home_team_name}</div>
                            <div style="font-size: 2rem; font-weight: 800; color: ${homeWinner ? 'var(--success-color)' : 'var(--secondary-color)'};">${game.home_score}</div>
                        </div>
                        <div style="color: var(--text-secondary);">VS</div>
                        <div class="team-score" style="text-align: center;">
                            <div style="font-weight: 600; margin-bottom: 4px; color: ${awayWinner ? 'var(--success-color)' : 'var(--text-secondary)'};">${game.away_team_name}</div>
                            <div style="font-size: 2rem; font-weight: 800; color: ${awayWinner ? 'var(--success-color)' : 'var(--secondary-color)'};">${game.away_score}</div>
                        </div>
                    </div>
                    ${seriesUpdate.team1_wins !== undefined ? `
                        <div class="series-score" style="text-align: center; color: var(--text-secondary); margin-bottom: 12px;">
                            系列赛比分: <strong>${seriesUpdate.team1_wins} - ${seriesUpdate.team2_wins}</strong>
                        </div>
                    ` : ''}
            `;
            
            // 添加球员统计数据（如果有）
            if (game.player_stats) {
                content += this.renderPlayoffAdvancePlayerStats(game);
            }
            
            content += '</div>';
        }
        
        content += '</div>';
        
        const footer = `
            <button class="btn btn-primary" onclick="GameApp.closeModal(); GameApp.loadDashboard();">
                继续
            </button>
        `;
        
        this.showModal('🏀 季后赛比赛结果', content, footer);
    },

    /**
     * 渲染季后赛推进比赛的球员统计数据
     */
    renderPlayoffAdvancePlayerStats(game) {
        const playerStats = game.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        // 如果没有球员数据，返回空
        if (homeStats.length === 0 && awayStats.length === 0) {
            return '';
        }
        
        return `
            <div class="player-stats-section" style="margin-top: 12px;">
                <details style="cursor: pointer;">
                    <summary style="font-weight: 600; color: var(--primary-color); padding: 8px 0;">
                        📊 查看球员数据统计
                    </summary>
                    <div class="stats-content" style="margin-top: 12px;">
                        <!-- 主队球员统计 -->
                        <div style="margin-bottom: 16px;">
                            <div style="font-weight: 600; margin-bottom: 8px; color: var(--secondary-color);">
                                🏠 ${game.home_team_name}
                            </div>
                            ${this.renderCompactPlayerStatsTable(homeStats)}
                        </div>
                        
                        <!-- 客队球员统计 -->
                        <div>
                            <div style="font-weight: 600; margin-bottom: 8px; color: var(--secondary-color);">
                                ✈️ ${game.away_team_name}
                            </div>
                            ${this.renderCompactPlayerStatsTable(awayStats)}
                        </div>
                    </div>
                </details>
            </div>
        `;
    },

    /**
     * 渲染紧凑的球员统计表格
     */
    renderCompactPlayerStatsTable(stats) {
        if (!stats || stats.length === 0) {
            return '<div style="color: var(--text-secondary); font-size: 0.9rem;">暂无数据</div>';
        }
        
        return `
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                <thead>
                    <tr style="background: var(--bg-secondary); text-align: center;">
                        <th style="padding: 6px; text-align: left;">球员</th>
                        <th style="padding: 6px;">得分</th>
                        <th style="padding: 6px;">篮板</th>
                        <th style="padding: 6px;">助攻</th>
                        <th style="padding: 6px;">抢断</th>
                        <th style="padding: 6px;">盖帽</th>
                    </tr>
                </thead>
                <tbody>
                    ${stats.map(p => `
                        <tr style="border-bottom: 1px solid var(--border-color); text-align: center;">
                            <td style="padding: 6px; text-align: left;">${p.player_name}</td>
                            <td style="padding: 6px; font-weight: 600;">${p.points}</td>
                            <td style="padding: 6px;">${p.rebounds}</td>
                            <td style="padding: 6px;">${p.assists}</td>
                            <td style="padding: 6px;">${p.steals}</td>
                            <td style="padding: 6px;">${p.blocks}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 格式化系列赛ID为可读名称
     */
    formatSeriesId(seriesId) {
        if (!seriesId) return '季后赛';
        
        const mapping = {
            'play_in_1': '附加赛 第1组',
            'play_in_2': '附加赛 第2组',
            'play_in_3': '附加赛 第3组',
            'play_in_4': '附加赛 第4组',
            'quarter_1': '四分之一决赛 第1组',
            'quarter_2': '四分之一决赛 第2组',
            'quarter_3': '四分之一决赛 第3组',
            'quarter_4': '四分之一决赛 第4组',
            'semi_1': '半决赛 第1组',
            'semi_2': '半决赛 第2组',
            'final': '总决赛'
        };
        
        return mapping[seriesId] || seriesId;
    },

    // ============================================
    // 阵容管理
    // ============================================
    async loadRoster() {
        const playerTeamId = this.state.gameState?.player_team?.id;
        if (!playerTeamId) {
            this.showToast('请先开始游戏', 'warning');
            return;
        }
        
        // 初始化阵容模式：默认显示常规赛数据
        if (!this.state.rosterMode) {
            this.state.rosterMode = 'regular';
        }
        
        // 加载所有球队列表（如果还没有）
        if (this.state.rosterTeamList.length === 0) {
            await this.loadAllTeamsForRoster();
        }
        
        // 每次进入阵容页面，默认显示玩家球队
        const playerTeamIndex = this.state.rosterTeamList.findIndex(t => t.id === playerTeamId);
        this.state.rosterTeamIndex = playerTeamIndex >= 0 ? playerTeamIndex : 0;
        
        // 更新模式按钮状态
        this.updateRosterModeButtons();
        
        // 更新球队切换控件
        this.updateTeamSwitcher();
        
        await this.refreshRoster();
    },

    async loadAllTeamsForRoster() {
        const response = await this.apiGet('/teams');
        if (response.success) {
            // 将玩家球队放在第一位，其他球队按名称排序
            const playerTeamId = this.state.gameState?.player_team?.id;
            const teams = response.data || [];
            const playerTeam = teams.find(t => t.id === playerTeamId);
            const otherTeams = teams.filter(t => t.id !== playerTeamId).sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
            this.state.rosterTeamList = playerTeam ? [playerTeam, ...otherTeams] : otherTeams;
        }
    },

    switchRosterTeam(direction) {
        const totalTeams = this.state.rosterTeamList.length;
        if (totalTeams === 0) return;
        
        this.state.rosterTeamIndex = (this.state.rosterTeamIndex + direction + totalTeams) % totalTeams;
        this.updateTeamSwitcher();
        this.refreshRoster();
    },

    updateTeamSwitcher() {
        const teams = this.state.rosterTeamList;
        const index = this.state.rosterTeamIndex;
        const currentTeam = teams[index];
        
        const nameEl = document.getElementById('roster-current-team-name');
        const indexEl = document.getElementById('roster-team-index');
        
        if (nameEl && currentTeam) {
            const playerTeamId = this.state.gameState?.player_team?.id;
            const isPlayerTeam = currentTeam.id === playerTeamId;
            nameEl.textContent = currentTeam.name + (isPlayerTeam ? ' (我的球队)' : '');
        }
        if (indexEl) {
            indexEl.textContent = `${index + 1}/${teams.length}`;
        }
    },

    switchRosterMode(mode) {
        this.state.rosterMode = mode;
        this.updateRosterModeButtons();
        this.refreshRoster();
    },

    updateRosterModeButtons() {
        const regularBtn = document.getElementById('btn-roster-regular');
        const playoffBtn = document.getElementById('btn-roster-playoff');
        const totalBtn = document.getElementById('btn-roster-total');
        
        if (regularBtn && playoffBtn && totalBtn) {
            const mode = this.state.rosterMode;
            regularBtn.classList.toggle('active', mode === 'regular');
            playoffBtn.classList.toggle('active', mode === 'playoff');
            totalBtn.classList.toggle('active', mode === 'total');
        }
    },

    async refreshRoster() {
        const teams = this.state.rosterTeamList;
        const index = this.state.rosterTeamIndex;
        const currentTeam = teams[index];
        
        if (!currentTeam) return;
        
        const teamId = currentTeam.id;
        const mode = this.state.rosterMode || 'regular';
        const response = await this.apiGet(`/team/${teamId}/roster?mode=${mode}`);
        if (!response.success) return;
        
        document.getElementById('roster-team-name').textContent = response.data.team.name;
        
        const tbody = document.getElementById('roster-body');
        if (!tbody) return;
        
        tbody.innerHTML = response.data.roster.map(player => `
            <tr class="player-row ${player.is_waived ? 'waived-player' : ''}" onclick="GameApp.showPlayerDetail('${player.id}')">
                <td>
                    <span class="player-name">${player.name}</span>
                    ${player.is_foreign ? '<span class="foreign-badge">外援</span>' : ''}
                    ${player.is_waived ? '<span class="waived-badge">被裁</span>' : ''}
                </td>
                <td><span class="player-position">${player.position}</span></td>
                <td>${player.age}</td>
                <td><span class="player-overall">${player.overall}</span></td>
                <td>${player.games_played}</td>
                <td>${player.avg_points}</td>
                <td>${player.avg_rebounds}</td>
                <td>${player.avg_assists}</td>
                <td>${player.avg_steals}</td>
                <td>${player.avg_blocks}</td>
                <td>
                    ${player.is_waived ? '<span class="waived-status">已裁</span>' : 
                      (player.is_injured ? `<span class="injured-badge">伤病 ${player.injury_days}天</span>` : '<span class="text-success">健康</span>')}
                </td>
            </tr>
        `).join('');
    },

    async showPlayerDetail(playerId) {
        const mode = this.state.rosterMode || 'regular';
        const response = await this.apiGet(`/player/${playerId}?mode=${mode}`);
        if (!response.success) return;
        
        const p = response.data;
        const isPlayerTeam = p.is_player_team;
        
        // 根据模式显示不同的标题
        const modeNames = {
            'regular': '常规赛',
            'playoff': '季后赛',
            'total': '总'
        };
        const modeName = modeNames[mode] || '赛季';
        
        // 训练进度信息（仅玩家球队显示）
        const tp = p.training_progress || {};
        const trainingPoints = tp.training_points || {};
        const attributeUpgrades = tp.attribute_upgrades || 0;
        const pointsPerUpgrade = tp.points_per_upgrade || 20;
        const upgradesPerOverall = tp.upgrades_per_overall || 5;
        
        // 根据是否是玩家球队决定属性显示方式
        const attributesHtml = isPlayerTeam ? `
            ${this.renderAttributeRowWithProgress('进攻', p.attributes.offense, trainingPoints.offense || 0, pointsPerUpgrade)}
            ${this.renderAttributeRowWithProgress('防守', p.attributes.defense, trainingPoints.defense || 0, pointsPerUpgrade)}
            ${this.renderAttributeRowWithProgress('三分', p.attributes.three_point, trainingPoints.three_point || 0, pointsPerUpgrade)}
            ${this.renderAttributeRowWithProgress('篮板', p.attributes.rebounding, trainingPoints.rebounding || 0, pointsPerUpgrade)}
            ${this.renderAttributeRowWithProgress('传球', p.attributes.passing, trainingPoints.passing || 0, pointsPerUpgrade)}
            ${this.renderAttributeRowWithProgress('体力', p.attributes.stamina, trainingPoints.stamina || 0, pointsPerUpgrade)}
        ` : `
            ${this.renderAttributeRow('进攻', p.attributes.offense)}
            ${this.renderAttributeRow('防守', p.attributes.defense)}
            ${this.renderAttributeRow('三分', p.attributes.three_point)}
            ${this.renderAttributeRow('篮板', p.attributes.rebounding)}
            ${this.renderAttributeRow('传球', p.attributes.passing)}
            ${this.renderAttributeRow('体力', p.attributes.stamina)}
        `;
        
        // 训练进度区块（仅玩家球队显示）
        const trainingProgressHtml = isPlayerTeam ? `
            <div class="player-training-progress">
                <h4>训练进度</h4>
                <div class="stat-row">
                    <span>总评提升进度</span>
                    <span>${attributeUpgrades}/${upgradesPerOverall}</span>
                </div>
                <div class="progress-bar-container" style="margin-top: 5px;">
                    <div class="progress-bar" style="width: ${(attributeUpgrades / upgradesPerOverall) * 100}%; background: linear-gradient(90deg, #ffc107, #ff9800);"></div>
                </div>
                <p class="text-muted" style="font-size: 0.85rem; margin-top: 5px;">累积${upgradesPerOverall}次属性+1后总评+1</p>
            </div>
        ` : '';
        
        const content = `
            <div class="player-detail">
                <div class="player-detail-top">
                    <div class="player-attributes">
                        <h4>基础属性</h4>
                        ${attributesHtml}
                        <div class="player-overall-display">
                            <span>总评</span>
                            <span class="overall-value">${p.overall}</span>
                        </div>
                    </div>
                    <div class="player-season-stats">
                        <h4>${modeName}场均数据</h4>
                        <div class="stat-row"><span>出场次数</span><span>${p.season_stats.games_played}</span></div>
                        <div class="stat-row"><span>得分</span><span>${p.season_stats.avg_points}</span></div>
                        <div class="stat-row"><span>篮板</span><span>${p.season_stats.avg_rebounds}</span></div>
                        <div class="stat-row"><span>助攻</span><span>${p.season_stats.avg_assists}</span></div>
                        <div class="stat-row"><span>抢断</span><span>${p.season_stats.avg_steals}</span></div>
                        <div class="stat-row"><span>盖帽</span><span>${p.season_stats.avg_blocks}</span></div>
                        <div class="stat-row"><span>失误</span><span>${p.season_stats.avg_turnovers}</span></div>
                        <div class="stat-row"><span>上场时间</span><span>${p.season_stats.avg_minutes}</span></div>
                    </div>
                </div>
                ${trainingProgressHtml}
            </div>
        `;
        
        this.showModal(`${p.basic_info.name} - ${p.basic_info.position}`, content);
    },

    renderAttributeRowWithProgress(label, value, trainingPoints, maxPoints) {
        const progressPercent = (trainingPoints / maxPoints) * 100;
        return `
            <div class="attribute-row">
                <span>${label}</span>
                <div class="attribute-bar">
                    <div class="attribute-fill" style="width: ${value}%"></div>
                </div>
                <span>${value}</span>
                <span class="training-progress-mini" title="训练进度: ${trainingPoints}/${maxPoints}">(${trainingPoints}/${maxPoints})</span>
            </div>
        `;
    },

    renderAttributeRow(label, value) {
        return `
            <div class="attribute-row">
                <span>${label}</span>
                <div class="attribute-bar">
                    <div class="attribute-fill" style="width: ${value}%"></div>
                </div>
                <span>${value}</span>
            </div>
        `;
    },


    // ============================================
    // 训练系统
    // ============================================
    async loadTraining() {
        // 先刷新游戏状态
        await this.refreshGameState();
        
        // 检查是否可以训练
        const state = this.state.gameState;
        const statusDiv = document.getElementById('training-status');
        const executeBtn = document.getElementById('btn-execute-training');
        
        // 检查是否在季后赛阶段
        if (state?.is_playoff_phase) {
            statusDiv.innerHTML = '<p class="text-warning">⚠️ 季后赛阶段无法进行训练</p>';
            executeBtn.disabled = true;
        } else if (state?.can_train === false) {
            // 使用后端返回的 can_train 字段判断
            statusDiv.innerHTML = '<p class="text-warning">⚠️ 今天有比赛，无法进行训练</p>';
            executeBtn.disabled = true;
        } else {
            statusDiv.innerHTML = '<p class="text-success">✅ 今天可以进行训练</p>';
        }
        
        // 加载训练状态（次数限制）
        await this.loadTrainingStatus();
        
        // 加载球队训练进度
        await this.loadTeamTrainingProgress();
        
        // 加载训练项目
        const programsResponse = await this.apiGet('/training/programs');
        if (programsResponse.success) {
            const container = document.getElementById('training-programs');
            // 按指定顺序排序：进攻、防守、三分、篮板、传球、体力
            const attributeOrder = ['offense', 'defense', 'three_point', 'rebounding', 'passing', 'stamina'];
            const sortedPrograms = [...programsResponse.data].sort((a, b) => {
                return attributeOrder.indexOf(a.target_attribute) - attributeOrder.indexOf(b.target_attribute);
            });
            container.innerHTML = sortedPrograms.map(p => `
                <div class="training-card" data-program="${p.name}" onclick="GameApp.selectTrainingProgram('${p.name}')">
                    <div class="training-name">${this.getTrainingDisplayName(p.name)}</div>
                    <div class="training-attribute">提升属性: ${p.target_attribute}</div>
                    <div class="training-boost">+${p.boost_min} ~ +${p.boost_max}</div>
                </div>
            `).join('');
        }
        
        // 加载球员列表
        const teamId = state?.player_team?.id;
        if (teamId) {
            const rosterResponse = await this.apiGet(`/team/${teamId}/roster`);
            if (rosterResponse.success) {
                const select = document.getElementById('training-player-select');
                // 存储球员数据用于显示剩余训练次数
                this.state.trainingRoster = rosterResponse.data.roster;
                
                // 获取每个球员的剩余训练次数
                const individualRemaining = this.state.trainingStatus?.individual_training_remaining || {};
                
                select.innerHTML = '<option value="">全队训练</option>' +
                    rosterResponse.data.roster.map(p => {
                        const injuredMark = p.is_injured ? ' 🤕' : '';
                        const remaining = individualRemaining[p.id]?.remaining ?? 0;
                        const completedMark = remaining <= 0 ? ' ✓' : '';
                        const isCompleted = remaining <= 0;
                        return `<option value="${p.id}" ${p.is_injured ? 'class="injured-option"' : ''} ${isCompleted ? 'style="color: #888;"' : ''}>${p.name} (${p.position})${injuredMark}${completedMark}</option>`;
                    }).join('');
                
                // 添加球员选择变化事件
                select.onchange = () => this.onTrainingPlayerChange();
            }
        }
        
        // 隐藏结果卡片
        document.getElementById('training-result-card')?.classList.add('hidden');
    },

    async loadTeamTrainingProgress(trainingResults = null, trainedAttribute = null) {
        const container = document.getElementById('team-training-progress');
        if (!container) return;
        
        const response = await this.apiGet('/training/team-progress');
        if (!response.success) {
            container.innerHTML = '<div class="text-center text-muted">加载失败</div>';
            return;
        }
        
        const data = response.data;
        const players = data.players;
        
        if (players.length === 0) {
            container.innerHTML = '<div class="text-center text-muted">暂无球员</div>';
            return;
        }
        
        // 将训练结果转换为以player_id为key的map，方便查找
        const resultsMap = {};
        if (trainingResults) {
            trainingResults.forEach(r => {
                resultsMap[r.player_id] = r;
            });
        }
        
        // 属性名称映射
        const attrNames = {
            'offense': '进攻',
            'defense': '防守',
            'three_point': '三分',
            'rebounding': '篮板',
            'passing': '传球',
            'stamina': '体力'
        };
        
        container.innerHTML = `
            <div class="table-container">
                <table class="table training-progress-table">
                    <thead>
                        <tr>
                            <th>球员</th>
                            <th>总评</th>
                            <th>进攻</th>
                            <th>防守</th>
                            <th>三分</th>
                            <th>篮板</th>
                            <th>传球</th>
                            <th>体力</th>
                            <th>总评进度</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${players.map(p => {
                            const tp = p.training_points;
                            const injuredClass = p.is_injured ? 'text-muted' : '';
                            const injuredBadge = p.is_injured ? ' 🤕' : '';
                            const result = resultsMap[p.player_id];
                            return `
                                <tr class="${injuredClass}">
                                    <td class="player-name-cell">
                                        <span class="player-name" style="cursor: pointer;" onclick="GameApp.showPlayerDetail('${p.player_id}')">
                                            ${p.player_name}${injuredBadge}
                                        </span>
                                        <small class="text-muted">(${p.position})</small>
                                    </td>
                                    <td class="overall-cell">${p.overall}${result && result.overall_upgraded ? '<span class="training-gain">+1</span>' : ''}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.offense, tp.offense, data.points_per_upgrade, trainedAttribute === 'offense' ? result : null)}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.defense, tp.defense, data.points_per_upgrade, trainedAttribute === 'defense' ? result : null)}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.three_point, tp.three_point, data.points_per_upgrade, trainedAttribute === 'three_point' ? result : null)}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.rebounding, tp.rebounding, data.points_per_upgrade, trainedAttribute === 'rebounding' ? result : null)}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.passing, tp.passing, data.points_per_upgrade, trainedAttribute === 'passing' ? result : null)}</td>
                                    <td>${this.renderTrainingPointCell(p.current_attributes.stamina, tp.stamina, data.points_per_upgrade, trainedAttribute === 'stamina' ? result : null)}</td>
                                    <td>${this.renderOverallProgressCell(p.attribute_upgrades, data.upgrades_per_overall, result)}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    renderTrainingPointCell(attrValue, trainingPoints, maxPoints, result = null) {
        const percent = (trainingPoints / maxPoints) * 100;
        let gainHtml = '';
        if (result && !result.skipped) {
            if (result.training_points_gained > 0) {
                gainHtml = `<span class="training-gain">+${result.training_points_gained}</span>`;
            }
            if (result.attribute_upgraded) {
                gainHtml += `<span class="training-upgrade">属性+1</span>`;
            }
        } else if (result && result.skipped) {
            gainHtml = `<span class="training-skipped">跳过</span>`;
        }
        return `
            <div class="training-cell">
                <div class="attr-value">${attrValue}</div>
                <div class="training-point-bar">
                    <div class="training-point-fill" style="width: ${percent}%"></div>
                </div>
                ${gainHtml ? `<div class="training-gain-row">${gainHtml}</div>` : ''}
                <div class="training-point-text">距+1: ${maxPoints - trainingPoints}</div>
            </div>
        `;
    },

    renderOverallProgressCell(upgrades, maxUpgrades, result = null) {
        const percent = (upgrades / maxUpgrades) * 100;
        let upgradeHtml = '';
        if (result && result.overall_upgraded) {
            upgradeHtml = `<span class="training-upgrade">总评+1</span>`;
        }
        return `
            <div class="overall-progress-cell">
                <div class="overall-progress-bar">
                    <div class="overall-progress-fill" style="width: ${percent}%"></div>
                </div>
                ${upgradeHtml ? `<div class="training-gain-row">${upgradeHtml}</div>` : ''}
                <div class="overall-progress-text">${upgrades}/${maxUpgrades}</div>
            </div>
        `;
    },

    async loadTrainingStatus() {
        const response = await this.apiGet('/training/status');
        if (response.success) {
            this.state.trainingStatus = response.data;
            
            // 更新全队训练剩余次数显示
            const teamRemaining = document.getElementById('team-training-remaining');
            if (teamRemaining) {
                teamRemaining.textContent = `${response.data.team_training_remaining}/${response.data.max_team_training}`;
            }
            
            // 更新单独训练上限显示
            const individualInfo = document.getElementById('individual-training-info');
            if (individualInfo) {
                individualInfo.textContent = `${response.data.max_individual_training}次`;
            }
        }
    },

    /**
     * 更新训练球员下拉列表（刷新训练完成标记）
     */
    updateTrainingPlayerSelect() {
        const select = document.getElementById('training-player-select');
        const roster = this.state.trainingRoster;
        const individualRemaining = this.state.trainingStatus?.individual_training_remaining || {};
        
        if (!select || !roster) return;
        
        // 保存当前选中的值
        const currentValue = select.value;
        
        select.innerHTML = '<option value="">全队训练</option>' +
            roster.map(p => {
                const injuredMark = p.is_injured ? ' 🤕' : '';
                const remaining = individualRemaining[p.id]?.remaining ?? 0;
                const completedMark = remaining <= 0 ? ' ✓' : '';
                const isCompleted = remaining <= 0;
                return `<option value="${p.id}" ${p.is_injured ? 'class="injured-option"' : ''} ${isCompleted ? 'style="color: #888;"' : ''}>${p.name} (${p.position})${injuredMark}${completedMark}</option>`;
            }).join('');
        
        // 恢复选中的值
        select.value = currentValue;
    },

    async onTrainingPlayerChange() {
        const playerId = document.getElementById('training-player-select')?.value;
        const remainingDiv = document.getElementById('player-training-remaining');
        const remainingCount = document.getElementById('player-remaining-count');
        const playerProgressDiv = document.getElementById('selected-player-progress');
        
        if (playerId && this.state.trainingStatus) {
            // 显示该球员的剩余训练次数
            const playerRemaining = this.state.trainingStatus.individual_training_remaining?.[playerId];
            if (playerRemaining !== undefined) {
                remainingDiv.style.display = 'block';
                remainingCount.textContent = playerRemaining.remaining;
            } else {
                remainingDiv.style.display = 'block';
                remainingCount.textContent = this.state.trainingStatus.max_individual_training;
            }
            
            // 加载并显示选中球员的训练进度
            await this.loadSelectedPlayerProgress(playerId);
        } else {
            // 全队训练，隐藏单独训练次数显示和球员进度
            remainingDiv.style.display = 'none';
            if (playerProgressDiv) {
                playerProgressDiv.style.display = 'none';
            }
        }
    },

    async loadSelectedPlayerProgress(playerId) {
        const playerProgressDiv = document.getElementById('selected-player-progress');
        if (!playerProgressDiv) return;
        
        const response = await this.apiGet(`/training/progress/${playerId}`);
        if (!response.success) {
            playerProgressDiv.style.display = 'none';
            return;
        }
        
        const p = response.data;
        const tp = p.training_points;
        
        playerProgressDiv.style.display = 'block';
        playerProgressDiv.innerHTML = `
            <div class="selected-player-progress-card">
                <h5>${p.player_name} 训练进度</h5>
                <div class="progress-grid">
                    <div class="progress-item">
                        <span>进攻 ${p.current_attributes.offense}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.offense / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.offense}/${p.points_per_upgrade}</span>
                    </div>
                    <div class="progress-item">
                        <span>防守 ${p.current_attributes.defense}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.defense / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.defense}/${p.points_per_upgrade}</span>
                    </div>
                    <div class="progress-item">
                        <span>三分 ${p.current_attributes.three_point}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.three_point / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.three_point}/${p.points_per_upgrade}</span>
                    </div>
                    <div class="progress-item">
                        <span>篮板 ${p.current_attributes.rebounding}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.rebounding / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.rebounding}/${p.points_per_upgrade}</span>
                    </div>
                    <div class="progress-item">
                        <span>传球 ${p.current_attributes.passing}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.passing / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.passing}/${p.points_per_upgrade}</span>
                    </div>
                    <div class="progress-item">
                        <span>体力 ${p.current_attributes.stamina}</span>
                        <div class="mini-progress-bar"><div class="mini-progress-fill" style="width: ${(tp.stamina / p.points_per_upgrade) * 100}%"></div></div>
                        <span class="progress-text">${tp.stamina}/${p.points_per_upgrade}</span>
                    </div>
                </div>
                <div class="overall-progress-section">
                    <span>总评进度 (${p.overall})</span>
                    <div class="overall-mini-progress-bar"><div class="overall-mini-progress-fill" style="width: ${(p.attribute_upgrades / p.upgrades_per_overall) * 100}%"></div></div>
                    <span class="progress-text">${p.attribute_upgrades}/${p.upgrades_per_overall}</span>
                </div>
            </div>
        `;
    },

    getTrainingDisplayName(name) {
        const names = {
            'offense_training': '进攻训练',
            'defense_training': '防守训练',
            'shooting_training': '投篮训练',
            'rebounding_training': '篮板训练',
            'passing_training': '传球训练',
            'stamina_training': '体能训练'
        };
        return names[name] || name;
    },

    selectTrainingProgram(programName) {
        this.state.selectedTrainingProgram = programName;
        
        document.querySelectorAll('.training-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.program === programName);
        });
        
        // 只有在可以训练时才启用按钮
        const state = this.state.gameState;
        const canTrain = state?.can_train !== false && !state?.is_playoff_phase;
        document.getElementById('btn-execute-training').disabled = !canTrain;
    },

    async showTrainingProgramProgress(programName) {
        // 获取训练项目对应的属性名
        const programToAttribute = {
            '投篮训练': 'three_point',
            '进攻训练': 'offense',
            '防守训练': 'defense',
            '篮板训练': 'rebounding',
            '传球训练': 'passing',
            '体能训练': 'stamina'
        };
        
        const attributeName = programToAttribute[programName];
        if (!attributeName) return;
        
        // 属性中文名映射
        const attrDisplayNames = {
            'three_point': '三分',
            'offense': '进攻',
            'defense': '防守',
            'rebounding': '篮板',
            'passing': '传球',
            'stamina': '体力'
        };
        
        // 获取球队训练进度数据
        const response = await this.apiGet('/training/team-progress');
        if (!response.success) return;
        
        const data = response.data;
        const players = data.players;
        
        // 统计伤病球员数量
        const injuredCount = players.filter(p => p.is_injured).length;
        const injuredNote = injuredCount > 0 ? `<p class="text-warning mb-1">⚠️ ${injuredCount}名球员受伤，训练时将被跳过</p>` : '';
        
        // 显示该训练项目的进度弹窗或面板
        const progressHtml = `
            <div class="training-program-progress-panel">
                <h4>📊 ${programName} - ${attrDisplayNames[attributeName]}属性进度</h4>
                <p class="text-muted mb-1">训练点数达到20时，该属性+1</p>
                ${injuredNote}
                <div class="table-container">
                    <table class="table training-program-progress-table">
                        <thead>
                            <tr>
                                <th>球员</th>
                                <th>状态</th>
                                <th>当前${attrDisplayNames[attributeName]}</th>
                                <th>训练进度</th>
                                <th>距离+1</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(p => {
                                const currentPoints = p.training_points[attributeName] || 0;
                                const currentAttr = p.current_attributes[attributeName] || 0;
                                const percent = (currentPoints / data.points_per_upgrade) * 100;
                                const remaining = data.points_per_upgrade - currentPoints;
                                const statusBadge = p.is_injured 
                                    ? '<span class="injured-badge">🤕 伤病</span>' 
                                    : '<span class="healthy-badge">✅ 健康</span>';
                                const rowClass = p.is_injured ? 'injured-row' : '';
                                return `
                                    <tr class="${rowClass}">
                                        <td><strong>${p.player_name}</strong> <small class="text-muted">(${p.position})</small></td>
                                        <td>${statusBadge}</td>
                                        <td><strong>${currentAttr}</strong></td>
                                        <td>
                                            <div class="progress-bar-container">
                                                <div class="progress-bar-fill ${p.is_injured ? 'injured-progress' : ''}" style="width: ${percent}%"></div>
                                            </div>
                                            <span class="progress-text">${currentPoints}/${data.points_per_upgrade}</span>
                                        </td>
                                        <td class="${remaining <= 5 ? 'text-warning' : ''}">${remaining}点</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        // 显示在训练结果区域
        const resultCard = document.getElementById('training-result-card');
        const resultDiv = document.getElementById('training-result');
        resultCard.classList.remove('hidden');
        resultDiv.innerHTML = progressHtml;
    },

    async executeTraining() {
        if (!this.state.selectedTrainingProgram) {
            this.showToast('请先选择训练项目', 'warning');
            return;
        }
        
        const playerId = document.getElementById('training-player-select')?.value || null;
        
        const response = await this.apiPost('/training/execute', {
            program_name: this.state.selectedTrainingProgram,
            player_id: playerId || undefined
        });
        
        if (response.success) {
            // 刷新训练状态
            await this.loadTrainingStatus();
            
            // 刷新球员下拉列表（更新训练完成标记）
            this.updateTrainingPlayerSelect();
            
            if (response.data.results) {
                // 全队训练结果 - 直接在进度表格中显示增量
                const remaining = response.data.team_training_remaining;
                const totalUpgrades = response.data.total_attribute_upgrades || 0;
                const totalOverallUpgrades = response.data.total_overall_upgrades || 0;
                
                // 刷新进度表格，传入训练结果
                await this.loadTeamTrainingProgress(response.data.results, response.data.target_attribute);
                
                // 显示简短的toast提示
                let toastMsg = `全队训练完成！（剩余${remaining}次）`;
                if (totalUpgrades > 0) {
                    toastMsg += ` ${totalUpgrades}人属性+1`;
                }
                if (totalOverallUpgrades > 0) {
                    toastMsg += ` ${totalOverallUpgrades}人总评+1`;
                }
                this.showToast(toastMsg, 'success');
            } else {
                // 单人训练结果 - 直接在进度表格中显示增量
                const d = response.data;
                const singleResult = [{
                    player_id: d.player_id,
                    player_name: d.player_name,
                    training_points_gained: d.training_points_gained,
                    current_training_points: d.current_training_points,
                    attribute_upgraded: d.attribute_upgraded,
                    overall_upgraded: d.overall_upgraded,
                    skipped: d.skipped || false
                }];
                
                // 刷新进度表格，传入训练结果
                await this.loadTeamTrainingProgress(singleResult, d.target_attribute);
                
                // 显示简短的toast提示
                let toastMsg = `${d.player_name} 训练完成！+${d.training_points_gained}`;
                if (d.attribute_upgraded) {
                    toastMsg += ` 属性+1`;
                }
                if (d.overall_upgraded) {
                    toastMsg += ` 总评+1`;
                }
                this.showToast(toastMsg, 'success');
                
                // 刷新该球员的剩余训练次数
                await this.loadSelectedPlayerProgress(playerId);
            }
            
            // 如果选中了球员，刷新该球员的进度
            const selectedPlayerId = document.getElementById('training-player-select')?.value;
            if (selectedPlayerId) {
                await this.loadSelectedPlayerProgress(selectedPlayerId);
            }
        } else {
            this.showToast(response.error?.message || '训练失败', 'error');
        }
    },

    // ============================================
    // 交易系统
    // ============================================
    async loadTrade() {
        this.state.selectedTradePlayers = { my: [], other: [] };
        
        // 加载我方可交易球员（排除外援）
        const teamId = this.state.gameState?.player_team?.id;
        if (teamId) {
            const response = await this.apiGet(`/trade/available-players/${teamId}`);
            if (response.success) {
                const container = document.getElementById('my-players-list');
                container.innerHTML = response.data.players.map(p => `
                    <div class="trade-player" data-player-id="${p.id}" onclick="GameApp.toggleTradePlayer('my', '${p.id}')">
                        <div>
                            <div class="player-name">${p.name}</div>
                            <div class="text-muted" style="font-size: 0.85rem;">
                                ${p.position} | ${p.age}岁 | 总评 ${p.overall}
                            </div>
                        </div>
                        <div class="player-overall">${p.overall}</div>
                    </div>
                `).join('');
            }
        }
        
        // 加载球队列表
        const teamsResponse = await this.apiGet('/teams');
        if (teamsResponse.success) {
            const select = document.getElementById('trade-team-select');
            select.innerHTML = '<option value="">选择交易对象球队</option>' +
                teamsResponse.data
                    .filter(t => t.id !== teamId)
                    .map(t => `<option value="${t.id}">${t.city}${t.name}</option>`)
                    .join('');
        }
    },

    async loadTradeTeamRoster() {
        const teamId = document.getElementById('trade-team-select')?.value;
        
        // 切换球队时，清空对方球员的选择列表
        this.state.selectedTradePlayers.other = [];
        
        // 更新交易按钮状态
        const canTrade = this.state.selectedTradePlayers.my.length > 0 && 
                        this.state.selectedTradePlayers.other.length > 0;
        document.getElementById('btn-propose-trade').disabled = !canTrade;
        
        if (!teamId) {
            document.getElementById('other-players-list').innerHTML = '';
            return;
        }
        
        // 使用可交易球员API（排除外援）
        const response = await this.apiGet(`/trade/available-players/${teamId}`);
        if (response.success) {
            const container = document.getElementById('other-players-list');
            container.innerHTML = response.data.players.map(p => `
                <div class="trade-player" data-player-id="${p.id}" onclick="GameApp.toggleTradePlayer('other', '${p.id}')">
                    <div>
                        <div class="player-name">${p.name}</div>
                        <div class="text-muted" style="font-size: 0.85rem;">
                            ${p.position} | ${p.age}岁 | 总评 ${p.overall}
                        </div>
                    </div>
                    <div class="player-overall">${p.overall}</div>
                </div>
            `).join('');
        }
    },

    toggleTradePlayer(side, playerId) {
        const players = this.state.selectedTradePlayers[side];
        const index = players.indexOf(playerId);
        
        if (index > -1) {
            players.splice(index, 1);
        } else {
            players.push(playerId);
        }
        
        // 更新UI
        const container = side === 'my' ? 'my-players-list' : 'other-players-list';
        document.querySelectorAll(`#${container} .trade-player`).forEach(el => {
            el.classList.toggle('selected', players.includes(el.dataset.playerId));
        });
        
        // 更新按钮状态
        const canTrade = this.state.selectedTradePlayers.my.length > 0 && 
                        this.state.selectedTradePlayers.other.length > 0;
        document.getElementById('btn-propose-trade').disabled = !canTrade;
    },

    async proposeTrade() {
        const receivingTeamId = document.getElementById('trade-team-select')?.value;
        if (!receivingTeamId) {
            this.showToast('请选择交易对象球队', 'warning');
            return;
        }
        
        const response = await this.apiPost('/trade/propose', {
            receiving_team_id: receivingTeamId,
            players_offered: this.state.selectedTradePlayers.my,
            players_requested: this.state.selectedTradePlayers.other
        });
        
        if (response.success) {
            this.showTradeResult(response.message, true);
            await this.loadTrade();
        } else {
            this.showTradeResult(response.error?.message || '交易被拒绝', false);
        }
    },

    showTradeResult(message, isSuccess) {
        const panel = document.getElementById('trade-result-panel');
        const icon = document.getElementById('trade-result-icon');
        const title = document.getElementById('trade-result-title');
        const content = document.getElementById('trade-result-content');
        
        if (!panel || !icon || !title || !content) return;
        
        // 设置样式
        panel.classList.remove('hidden', 'success', 'error');
        panel.classList.add(isSuccess ? 'success' : 'error');
        
        // 设置内容
        icon.textContent = isSuccess ? '✅' : '❌';
        title.textContent = isSuccess ? '交易成功' : '交易被拒绝';
        content.textContent = message;
        
        // 滚动到结果面板
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    closeTradeResult() {
        const panel = document.getElementById('trade-result-panel');
        if (panel) {
            panel.classList.add('hidden');
        }
    },

    switchTradeTab(tab) {
        document.querySelectorAll('.leaderboard-tab').forEach(el => {
            el.classList.toggle('active', el.dataset.tab === tab);
        });
        
        document.getElementById('trade-panel').classList.toggle('hidden', tab !== 'trade');
        document.getElementById('foreign-market-panel').classList.toggle('hidden', tab !== 'foreign-market');
        
        // 如果切换到外援市场，加载外援市场信息
        if (tab === 'foreign-market') {
            this.loadForeignMarketInfo();
        }
    },

    async loadForeignMarketInfo() {
        const response = await this.apiGet('/foreign-market/info');
        if (!response.success) return;
        
        const data = response.data;
        
        // 更新经费显示
        document.getElementById('team-budget').textContent = data.budget;
        document.getElementById('scout-cost').textContent = data.scout_cost;
        document.getElementById('scout-cost-btn').textContent = data.scout_cost;
        document.getElementById('targeted-scout-cost').textContent = data.targeted_scout_cost;
        document.getElementById('targeted-scout-cost-btn').textContent = data.targeted_scout_cost;
        document.getElementById('foreign-count').textContent = data.foreign_count;
        
        // 更新外援上限显示
        const maxForeignEl = document.getElementById('max-foreign');
        if (maxForeignEl) {
            maxForeignEl.textContent = data.max_foreign;
        }
        
        // 更新赞助系统状态
        if (data.sponsor_status) {
            this.updateSponsorStatus(data.sponsor_status);
        }
        
        // 更新普通搜索按钮状态
        const scoutBtn = document.getElementById('btn-scout-foreign');
        const scoutReason = document.getElementById('scout-reason');
        
        if (data.can_scout) {
            scoutBtn.disabled = false;
            scoutReason.textContent = '';
        } else {
            scoutBtn.disabled = true;
            scoutReason.textContent = data.scout_reason;
        }
        
        // 更新定向搜索按钮状态
        const targetedScoutBtn = document.getElementById('btn-targeted-scout');
        const targetedScoutReason = document.getElementById('targeted-scout-reason');
        
        if (data.can_targeted_scout) {
            targetedScoutBtn.disabled = false;
            targetedScoutReason.textContent = '';
        } else {
            targetedScoutBtn.disabled = true;
            targetedScoutReason.textContent = data.targeted_scout_reason;
        }
        
        // 如果有搜索到的外援，显示所有外援
        if (data.scouted_players && data.scouted_players.length > 0) {
            this.displayScoutedPlayers(data.scouted_players);
        } else {
            document.getElementById('scouted-players-container').innerHTML = '';
        }
    },

    displayScoutedPlayers(players) {
        const container = document.getElementById('scouted-players-container');
        container.innerHTML = players.map((player, index) => this.createScoutedPlayerCard(player, index)).join('');
    },

    createScoutedPlayerCard(player, index) {
        const visibleAttrs = player.visible_attributes || {};
        const remainingDays = player.remaining_days !== undefined ? player.remaining_days : 20;
        let remainingClass = 'remaining-days-badge';
        if (remainingDays <= 3) {
            remainingClass += ' danger';
        } else if (remainingDays <= 7) {
            remainingClass += ' warning';
        }
        
        const searchTypeBadge = player.is_targeted_search 
            ? '<span class="badge" style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; margin-left: 8px;">定向搜索</span>'
            : '<span class="badge" style="background-color: #007bff; color: white; padding: 2px 8px; border-radius: 4px; margin-left: 8px;">普通搜索</span>';
        
        const tagsHtml = player.skill_tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        
        return `
            <div class="card mb-2" id="scouted-player-card-${index}">
                <div class="card-header">⭐ 搜索到的外援 #${index + 1} ${searchTypeBadge}</div>
                <div class="card-body">
                    <div class="scouted-player-info">
                        <div class="scouted-player-header">
                            <div class="scouted-player-name">${player.name}</div>
                            <div class="scouted-player-overall">??</div>
                        </div>
                        <div class="scouted-player-basic">
                            ${player.position} | ${player.age}岁 |
                            💰 工资：${player.salary}万元 |
                            ⏰ 剩余：<span class="${remainingClass}">${remainingDays}</span>天
                        </div>
                        <div class="scouted-player-tags mt-1">${tagsHtml}</div>
                        
                        <div class="scouted-player-attrs mt-2">
                            <div class="attr-row">
                                <span class="attr-label">进攻</span>
                                <span class="attr-value">${visibleAttrs['进攻'] !== undefined ? visibleAttrs['进攻'] : '??'}</span>
                            </div>
                            <div class="attr-row">
                                <span class="attr-label">防守</span>
                                <span class="attr-value">${visibleAttrs['防守'] !== undefined ? visibleAttrs['防守'] : '??'}</span>
                            </div>
                            <div class="attr-row">
                                <span class="attr-label">三分</span>
                                <span class="attr-value">${visibleAttrs['三分'] !== undefined ? visibleAttrs['三分'] : '??'}</span>
                            </div>
                            <div class="attr-row">
                                <span class="attr-label">篮板</span>
                                <span class="attr-value">${visibleAttrs['篮板'] !== undefined ? visibleAttrs['篮板'] : '??'}</span>
                            </div>
                            <div class="attr-row">
                                <span class="attr-label">传球</span>
                                <span class="attr-value">${visibleAttrs['传球'] !== undefined ? visibleAttrs['传球'] : '??'}</span>
                            </div>
                            <div class="attr-row">
                                <span class="attr-label">体力</span>
                                <span class="attr-value">${visibleAttrs['体力'] !== undefined ? visibleAttrs['体力'] : '??'}</span>
                            </div>
                        </div>
                        <p class="text-muted mt-1" style="font-size: 0.8rem;">💡 只有3项能力值已知，其他为未知。总评在签约后揭晓。</p>
                        
                        <div class="scouted-player-career mt-2">
                            <div class="career-title">📜 过往经历</div>
                            <div class="career-content">${player.career_background}</div>
                        </div>
                        
                        <div class="scouted-player-report mt-2">
                            <div class="report-title">📋 球探报告</div>
                            <div class="report-content">${player.scouting_report}</div>
                        </div>
                    </div>
                    
                    <div class="scouted-player-actions mt-2">
                        <button class="btn btn-success btn-lg" onclick="GameApp.signScoutedPlayer('${player.id}')">
                            ✅ 签约 (支付 ${player.salary} 万元)
                        </button>
                        <button class="btn btn-secondary btn-lg" onclick="GameApp.dismissScoutedPlayer('${player.id}')">
                            ❌ 放弃
                        </button>
                    </div>
                </div>
            </div>
        `;
    },

    displayScoutedPlayer(player) {
        // 向后兼容：单个外援显示
        this.displayScoutedPlayers([player]);
    },

    async scoutForeignPlayer(targeted = false) {
        const btn = targeted ? document.getElementById('btn-targeted-scout') : document.getElementById('btn-scout-foreign');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '🔍 搜索中...';
        
        try {
            const requestData = { use_llm: true, targeted: targeted };
            if (targeted) {
                requestData.target_position = document.getElementById('target-position-select').value;
            }
            
            const response = await this.apiPost('/foreign-market/scout', requestData);
            
            if (response.success) {
                this.showToast(response.message, 'success');
                
                // 更新经费显示
                document.getElementById('team-budget').textContent = response.data.current_budget;
                
                // 显示所有搜索到的外援
                if (response.data.scouted_players && response.data.scouted_players.length > 0) {
                    this.displayScoutedPlayers(response.data.scouted_players);
                }
                
                // 更新搜索按钮状态
                await this.loadForeignMarketInfo();
            } else {
                this.showToast(response.error?.message || '搜索失败', 'error');
            }
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },

    async signScoutedPlayer(scoutedPlayerId = null, replacePlayerId = null) {
        const requestData = {};
        if (scoutedPlayerId) {
            requestData.scouted_player_id = scoutedPlayerId;
        }
        if (replacePlayerId) {
            requestData.replace_player_id = replacePlayerId;
        }
        const response = await this.apiPost('/foreign-market/sign', requestData);
        
        if (response.success) {
            // 签约成功，显示完整信息
            const fullInfo = response.data.player_full_info;
            if (fullInfo) {
                this.showToast(`${response.message}\n实际能力值 - 总评:${fullInfo.overall} 进攻:${fullInfo.offense} 防守:${fullInfo.defense} 三分:${fullInfo.three_point} 篮板:${fullInfo.rebounding} 传球:${fullInfo.passing} 体力:${fullInfo.stamina}`, 'success');
            } else {
                this.showToast(response.message, 'success');
            }
            // 隐藏替换面板
            const replacePanel = document.getElementById('replace-foreign-panel');
            if (replacePanel) {
                replacePanel.style.display = 'none';
            }
            // 重新加载外援市场信息
            await this.loadForeignMarketInfo();
        } else {
            // 检查是否需要替换外援
            if (response.error?.code === 'NEEDS_REPLACEMENT' && response.data?.needs_replacement) {
                // 保存当前要签约的外援ID
                this.state.pendingSignPlayerId = scoutedPlayerId;
                this.showReplaceForeignPanel(response.data.foreign_players);
                this.showToast(response.error.message, 'warning');
            } else {
                this.showToast(response.error?.message || '签约失败', 'error');
            }
        }
    },

    showReplaceForeignPanel(foreignPlayers) {
        // 获取或创建替换面板
        let replacePanel = document.getElementById('replace-foreign-panel');
        if (!replacePanel) {
            // 创建替换面板
            replacePanel = document.createElement('div');
            replacePanel.id = 'replace-foreign-panel';
            replacePanel.className = 'card mb-2';
            // 插入到外援容器后面
            const container = document.getElementById('scouted-players-container');
            container.parentNode.insertBefore(replacePanel, container.nextSibling);
        }
        
        replacePanel.style.display = 'block';
        replacePanel.innerHTML = `
            <div class="card-header" style="background: #dc3545; color: white;">⚠️ 选择要替换的外援</div>
            <div class="card-body">
                <p class="text-muted mb-2">外援名额已满，请选择一名外援进行替换。被替换的外援将被标记为"被裁"状态，仍会显示在阵容中但不再出战比赛。</p>
                <div id="replace-foreign-list"></div>
                <div class="mt-2">
                    <button class="btn btn-secondary" onclick="GameApp.cancelReplacement()">取消</button>
                </div>
            </div>
        `;
        
        // 填充外援列表
        const listContainer = document.getElementById('replace-foreign-list');
        listContainer.innerHTML = foreignPlayers.map(player => `
            <div class="replace-foreign-item" style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 10px; background: #f8f9fa;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: bold; font-size: 1.1rem;">${player.name}</div>
                        <div style="color: #666; font-size: 0.9rem;">
                            ${player.position} | ${player.age}岁 | 总评: <strong>${player.overall}</strong>
                        </div>
                        <div style="color: #666; font-size: 0.85rem; margin-top: 4px;">
                            进攻:${player.offense} 防守:${player.defense} 三分:${player.three_point} 篮板:${player.rebounding} 传球:${player.passing} 体力:${player.stamina}
                        </div>
                        <div style="color: #888; font-size: 0.85rem; margin-top: 4px;">
                            本赛季: ${player.games_played}场 | 场均 ${player.avg_points}分 ${player.avg_rebounds}篮板 ${player.avg_assists}助攻
                        </div>
                        ${player.skill_tags && player.skill_tags.length > 0 ? `
                            <div style="margin-top: 4px;">
                                ${player.skill_tags.map(tag => `<span class="tag" style="background: #007bff; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; margin-right: 4px;">${tag}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                    <button class="btn btn-danger" onclick="GameApp.confirmReplacement('${player.id}', '${player.name}')">
                        替换
                    </button>
                </div>
            </div>
        `).join('');
        
        replacePanel.style.display = 'block';
        // 滚动到替换面板
        replacePanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    },

    confirmReplacement(replacePlayerId, playerName) {
        if (confirm(`确定要替换外援 ${playerName} 吗？\n\n被替换的外援将被标记为"被裁"状态，仍会显示在阵容中但不再出战比赛，统计数据也不再变化。`)) {
            // 使用保存的待签约外援ID和要替换的外援ID
            this.signScoutedPlayer(this.state.pendingSignPlayerId, replacePlayerId);
        }
    },

    cancelReplacement() {
        const replacePanel = document.getElementById('replace-foreign-panel');
        if (replacePanel) {
            replacePanel.style.display = 'none';
        }
        // 清除待签约外援ID
        this.state.pendingSignPlayerId = null;
    },

    async dismissScoutedPlayer(playerId = null) {
        const requestData = playerId ? { player_id: playerId } : {};
        const response = await this.apiPost('/foreign-market/dismiss', requestData);
        
        if (response.success) {
            this.showToast(response.message || '已放弃该外援', 'info');
            // 重新加载外援市场信息
            await this.loadForeignMarketInfo();
        } else {
            this.showToast(response.error?.message || '操作失败', 'error');
        }
    },

    // 更新赞助系统状态
    updateSponsorStatus(status) {
        const sponsorBtn = document.getElementById('btn-get-sponsor');
        const sponsorStatus = document.getElementById('sponsor-status');
        const cooldownDays = document.getElementById('sponsor-cooldown-days');
        const sponsorMin = document.getElementById('sponsor-min');
        const sponsorMax = document.getElementById('sponsor-max');
        
        if (cooldownDays) cooldownDays.textContent = status.cooldown_days;
        if (sponsorMin) sponsorMin.textContent = status.min_amount;
        if (sponsorMax) sponsorMax.textContent = status.max_amount;
        
        if (status.can_sponsor) {
            sponsorBtn.disabled = false;
            sponsorStatus.textContent = '✅ 可以拉赞助';
            sponsorStatus.style.color = '#28a745';
        } else {
            sponsorBtn.disabled = true;
            sponsorStatus.textContent = `⏳ ${status.reason}`;
            sponsorStatus.style.color = '#dc3545';
        }
    },

    // 拉赞助
    async getSponsor() {
        const response = await this.apiPost('/foreign-market/sponsor');
        
        if (response.success) {
            const amount = response.data.amount;
            let toastType = 'success';
            let message = response.message;
            
            // 根据金额显示不同效果
            if (amount >= 80) {
                toastType = 'success';
                message = `🎉 ${message}`;
            } else if (amount >= 50) {
                toastType = 'success';
                message = `💰 ${message}`;
            } else {
                toastType = 'info';
            }
            
            this.showToast(message, toastType);
            
            // 更新经费显示
            document.getElementById('team-budget').textContent = response.data.current_budget;
            
            // 更新赞助状态
            if (response.data.sponsor_status) {
                this.updateSponsorStatus(response.data.sponsor_status);
            }
        } else {
            this.showToast(response.message, 'error');
        }
    },

    async loadFreeAgents() {
        // 保留旧函数以兼容，但不再使用
    },

    async signFreeAgent(playerId) {
        // 保留旧函数以兼容，但不再使用
    },

    // ============================================
    // 比赛系统
    // ============================================
    async loadMatch() {
        await this.refreshGameState();
        const state = this.state.gameState;
        
        // 隐藏所有面板
        document.getElementById('pre-match-panel')?.classList.add('hidden');
        document.getElementById('match-result-panel')?.classList.add('hidden');
        document.getElementById('no-match-panel')?.classList.add('hidden');
        document.getElementById('llm-simulating-panel')?.classList.add('hidden');
        
        // 检查是否有玩家球队比赛
        if (!state?.has_player_match_today || !state?.today_game) {
            // 今日无玩家球队比赛
            document.getElementById('no-match-panel')?.classList.remove('hidden');
            return;
        }
        
        // 检查比赛是否已完成
        if (state?.player_match_completed_today) {
            // 比赛已完成，显示结果
            this.showToast('今日比赛已完成', 'info');
            this.showPage('dashboard');
            return;
        }
        
        // 显示比赛前面板
        document.getElementById('pre-match-panel')?.classList.remove('hidden');
        
        // 设置球队名称 (Requirements 6.2, 6.3 - 只显示玩家球队比赛)
        const homeTeam = state.today_game.is_home ? state.player_team?.name : state.today_game.opponent_name;
        const awayTeam = state.today_game.is_home ? state.today_game.opponent_name : state.player_team?.name;
        
        document.getElementById('pre-home-team').textContent = homeTeam;
        document.getElementById('pre-away-team').textContent = awayTeam;
    },

    /**
     * 开始比赛 - 调用玩家比赛模拟API（快速模拟）
     */
    async startMatch() {
        // 显示模拟中状态并启动进度条
        this.showLlmSimulatingPanel();
        this.startProgressAnimation();
        
        try {
            // 调用玩家比赛模拟API
            const response = await this.apiPost('/match/simulate-player', {}, { skipLoading: true });
            
            // 完成进度条并隐藏
            this.completeProgressAnimation();
            
            if (!response.success) {
                this.showToast(response.error?.message || '比赛模拟失败', 'error');
                document.getElementById('pre-match-panel')?.classList.remove('hidden');
                return;
            }
            
            // 显示比赛结果
            await this.showMatchResult(response.data);
            
            // 显示伤病信息
            if (response.data.new_injuries && response.data.new_injuries.length > 0) {
                const injuryNames = response.data.new_injuries.map(i => i.player_name).join('、');
                this.showToast(`⚠️ 伤病: ${injuryNames}`, 'warning');
            }
            
        } catch (error) {
            this.stopProgressAnimation();
            this.hideLlmSimulatingPanel();
            this.showToast('比赛模拟出错: ' + error.message, 'error');
            document.getElementById('pre-match-panel')?.classList.remove('hidden');
        }
    },

    // 进度条动画相关
    progressInterval: null,
    progressValue: 0,

    /**
     * 启动进度条动画
     */
    startProgressAnimation() {
        this.progressValue = 0;
        const progressBar = document.getElementById('match-progress-bar');
        const progressText = document.getElementById('match-progress-text');
        
        if (progressBar) progressBar.style.width = '0%';
        
        const stages = [
            { progress: 20, text: '准备比赛数据...' },
            { progress: 40, text: '模拟第一节...' },
            { progress: 60, text: '模拟第二节...' },
            { progress: 75, text: '模拟第三节...' },
            { progress: 85, text: '模拟第四节...' },
            { progress: 92, text: '生成球员统计...' }
        ];
        
        let stageIndex = 0;
        
        this.progressInterval = setInterval(() => {
            if (stageIndex < stages.length) {
                const stage = stages[stageIndex];
                this.progressValue = stage.progress;
                if (progressBar) progressBar.style.width = `${stage.progress}%`;
                if (progressText) progressText.textContent = stage.text;
                stageIndex++;
            }
        }, 800);
    },

    /**
     * 完成进度条动画
     */
    completeProgressAnimation() {
        this.stopProgressAnimation();
        const progressBar = document.getElementById('match-progress-bar');
        const progressText = document.getElementById('match-progress-text');
        
        if (progressBar) progressBar.style.width = '100%';
        if (progressText) progressText.textContent = '比赛完成！';
        
        // 短暂延迟后隐藏
        setTimeout(() => {
            this.hideLlmSimulatingPanel();
        }, 300);
    },

    /**
     * 停止进度条动画
     */
    stopProgressAnimation() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    },

    /**
     * 显示模拟中面板
     * 同时显示遮罩层阻止用户点击其他按钮
     */
    showLlmSimulatingPanel() {
        document.getElementById('pre-match-panel')?.classList.add('hidden');
        document.getElementById('match-result-panel')?.classList.add('hidden');
        document.getElementById('no-match-panel')?.classList.add('hidden');
        document.getElementById('llm-simulating-panel')?.classList.remove('hidden');
        
        // 显示遮罩层阻止用户操作
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            // 隐藏遮罩层的文字，因为进度条面板已经有提示了
            const loadingText = overlay.querySelector('.loading-text');
            const loadingSpinner = overlay.querySelector('.loading-spinner');
            if (loadingText) loadingText.style.display = 'none';
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            overlay.style.display = 'flex';
            overlay.style.background = 'rgba(0, 0, 0, 0.3)';
        }
    },

    /**
     * 隐藏模拟中面板
     * 同时隐藏遮罩层
     */
    hideLlmSimulatingPanel() {
        document.getElementById('llm-simulating-panel')?.classList.add('hidden');
        
        // 隐藏遮罩层并恢复默认样式
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
            // 恢复默认样式
            const loadingText = overlay.querySelector('.loading-text');
            const loadingSpinner = overlay.querySelector('.loading-spinner');
            if (loadingText) loadingText.style.display = '';
            if (loadingSpinner) loadingSpinner.style.display = '';
            overlay.style.background = '';
        }
    },

    /**
     * 显示比赛结果
     * @param {Object} matchResult - 比赛结果数据
     */
    async showMatchResult(matchResult) {
        // 隐藏其他面板，显示结果面板
        document.getElementById('pre-match-panel')?.classList.add('hidden');
        document.getElementById('llm-simulating-panel')?.classList.add('hidden');
        document.getElementById('match-result-panel')?.classList.remove('hidden');
        
        // 设置比分
        document.getElementById('result-home-team').textContent = matchResult.home_team_name;
        document.getElementById('result-away-team').textContent = matchResult.away_team_name;
        document.getElementById('result-home-score').textContent = matchResult.home_score;
        document.getElementById('result-away-score').textContent = matchResult.away_score;
        
        // 显示球员数据统计
        this.renderBoxScoreFromResult(matchResult);
    },

    /**
     * 从比赛结果渲染球员数据统计
     * @param {Object} matchResult - 比赛结果数据
     */
    renderBoxScoreFromResult(matchResult) {
        const playerStats = matchResult.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        // 主队数据
        document.getElementById('home-box-score-header').textContent = `${matchResult.home_team_name} 数据统计`;
        const homeBody = document.getElementById('home-box-score-body');
        homeBody.innerHTML = homeStats.map(p => `
            <tr>
                <td>${p.player_name}</td>
                <td>${p.points}</td>
                <td>${p.rebounds}</td>
                <td>${p.assists}</td>
                <td>${p.steals}</td>
                <td>${p.blocks}</td>
                <td>${p.turnovers}</td>
                <td>${p.minutes || '-'}</td>
            </tr>
        `).join('') || '<tr><td colspan="8" class="text-center text-muted">暂无数据</td></tr>';
        
        // 客队数据
        document.getElementById('away-box-score-header').textContent = `${matchResult.away_team_name} 数据统计`;
        const awayBody = document.getElementById('away-box-score-body');
        awayBody.innerHTML = awayStats.map(p => `
            <tr>
                <td>${p.player_name}</td>
                <td>${p.points}</td>
                <td>${p.rebounds}</td>
                <td>${p.assists}</td>
                <td>${p.steals}</td>
                <td>${p.blocks}</td>
                <td>${p.turnovers}</td>
                <td>${p.minutes || '-'}</td>
            </tr>
        `).join('') || '<tr><td colspan="8" class="text-center text-muted">暂无数据</td></tr>';
    },

    renderBoxScore(gameData, matchResult) {
        const playerStats = gameData.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        // 主队数据
        document.getElementById('home-box-score-header').textContent = `${matchResult.home_team_name} 数据统计`;
        const homeBody = document.getElementById('home-box-score-body');
        homeBody.innerHTML = homeStats.map(p => `
            <tr>
                <td>${p.player_name}</td>
                <td>${p.points}</td>
                <td>${p.rebounds}</td>
                <td>${p.assists}</td>
                <td>${p.steals}</td>
                <td>${p.blocks}</td>
                <td>${p.turnovers}</td>
                <td>${p.minutes}</td>
            </tr>
        `).join('') || '<tr><td colspan="8" class="text-center text-muted">暂无数据</td></tr>';
        
        // 客队数据
        document.getElementById('away-box-score-header').textContent = `${matchResult.away_team_name} 数据统计`;
        const awayBody = document.getElementById('away-box-score-body');
        awayBody.innerHTML = awayStats.map(p => `
            <tr>
                <td>${p.player_name}</td>
                <td>${p.points}</td>
                <td>${p.rebounds}</td>
                <td>${p.assists}</td>
                <td>${p.steals}</td>
                <td>${p.blocks}</td>
                <td>${p.turnovers}</td>
                <td>${p.minutes}</td>
            </tr>
        `).join('') || '<tr><td colspan="8" class="text-center text-muted">暂无数据</td></tr>';
    },

    async continueAfterMatch() {
        await this.refreshGameState();
        this.showPage('dashboard');
        this.showToast('比赛结束，继续游戏', 'success');
    },

    // ============================================
    // 排行榜系统
    // ============================================
    async loadLeaderboard() {
        this.state.currentLeaderboardStat = 'points';
        // 初始化排行榜模式：默认显示常规赛数据
        this.state.leaderboardMode = 'regular';
        // 初始化球员筛选：默认显示所有球员
        this.state.leaderboardPlayerFilter = 'all';
        
        // 更新模式按钮状态
        this.updateLeaderboardModeButtons();
        
        // 更新球员筛选按钮状态
        document.getElementById('btn-all-players')?.classList.add('active');
        document.getElementById('btn-domestic-players')?.classList.remove('active');
        
        // 更新筛选条件显示
        this.updateLeaderboardFilters();
        
        await this.refreshLeaderboard();
    },

    switchLeaderboardMode(mode) {
        this.state.leaderboardMode = mode;
        this.updateLeaderboardModeButtons();
        this.updateLeaderboardFilters();
        
        // 如果是球队战绩榜模式，直接加载球队战绩
        if (mode === 'team-standings') {
            this.loadTeamStandingsLeaderboard();
        } else {
            this.refreshLeaderboard();
        }
    },

    updateLeaderboardModeButtons() {
        const playoffBtn = document.getElementById('btn-playoff-mode');
        const regularBtn = document.getElementById('btn-regular-mode');
        const totalBtn = document.getElementById('btn-total-mode');
        const teamStandingsBtn = document.getElementById('btn-team-standings-mode');
        
        const mode = this.state.leaderboardMode;
        
        playoffBtn?.classList.toggle('active', mode === 'playoff');
        regularBtn?.classList.toggle('active', mode === 'regular');
        totalBtn?.classList.toggle('active', mode === 'total');
        teamStandingsBtn?.classList.toggle('active', mode === 'team-standings');
        
        // 根据模式显示/隐藏相应的卡片
        const playerCard = document.getElementById('player-leaderboard-card');
        const teamCard = document.getElementById('team-standings-leaderboard-card');
        const tabsDiv = document.getElementById('leaderboard-tabs');
        const playerFilterDiv = document.getElementById('leaderboard-player-filter');
        
        if (mode === 'team-standings') {
            playerCard?.classList.add('hidden');
            teamCard?.classList.remove('hidden');
            tabsDiv?.classList.add('hidden');
            playerFilterDiv?.classList.add('hidden');
        } else {
            playerCard?.classList.remove('hidden');
            teamCard?.classList.add('hidden');
            tabsDiv?.classList.remove('hidden');
            playerFilterDiv?.classList.remove('hidden');
        }
    },

    updateLeaderboardFilters() {
        const minGamesGroup = document.getElementById('min-games-group');
        const filtersCard = document.getElementById('leaderboard-filters-card');
        const mode = this.state.leaderboardMode;
        
        // 球队战绩榜不需要筛选条件
        if (mode === 'team-standings') {
            filtersCard?.classList.add('hidden');
            return;
        }
        
        filtersCard?.classList.remove('hidden');
        
        if (minGamesGroup) {
            // 季后赛模式下隐藏"最少出场次数"选项
            minGamesGroup.style.display = this.state.leaderboardMode === 'playoff' ? 'none' : 'block';
        }
    },

    async switchLeaderboard(statType) {
        this.state.currentLeaderboardStat = statType;
        
        // 更新标签页高亮
        document.querySelectorAll('.leaderboard-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.stat === statType);
        });
        
        await this.refreshLeaderboard();
    },

    /**
     * 切换球员筛选类型（所有球员/本土球员）
     */
    async switchPlayerFilter(filterType) {
        this.state.leaderboardPlayerFilter = filterType;
        
        // 更新按钮高亮
        document.getElementById('btn-all-players')?.classList.toggle('active', filterType === 'all');
        document.getElementById('btn-domestic-players')?.classList.toggle('active', filterType === 'domestic');
        
        await this.refreshLeaderboard();
    },

    async loadTeamStandingsLeaderboard() {
        const response = await this.apiGet('/leaderboard/team-standings');
        
        if (!response.success) {
            this.showToast(response.error?.message || '加载球队战绩榜失败', 'error');
            return;
        }
        
        const data = response.data;
        const tbody = document.getElementById('team-standings-leaderboard-body');
        const noData = document.getElementById('no-team-standings-data');
        
        if (!data.leaderboard || data.leaderboard.length === 0) {
            tbody.innerHTML = '';
            noData?.classList.remove('hidden');
            return;
        }
        
        noData?.classList.add('hidden');
        
        // 渲染球队战绩表格
        tbody.innerHTML = data.leaderboard.map((entry, index) => {
            const isPlayerTeam = entry.team_id === this.state.gameState?.player_team?.id;
            return `
                <tr class="${isPlayerTeam ? 'table-primary' : ''}">
                    <td>
                        <span class="rank-badge ${index < 3 ? 'rank-top' : ''} ${index < 12 ? 'rank-playoff' : ''}">${entry.rank}</span>
                    </td>
                    <td>
                        <strong>${entry.team_name}</strong>
                        ${isPlayerTeam ? '<span class="badge badge-primary ms-1">我的球队</span>' : ''}
                    </td>
                    <td>${entry.wins}</td>
                    <td>${entry.losses}</td>
                    <td><strong>${(entry.win_pct * 100).toFixed(1)}%</strong></td>
                    <td>${entry.games_behind === 0 ? '-' : entry.games_behind.toFixed(1)}</td>
                </tr>
            `;
        }).join('');
    },

    async refreshLeaderboard() {
        const statType = this.state.currentLeaderboardStat;
        const minGames = document.getElementById('min-games-select')?.value || 5;
        const topN = document.getElementById('top-n-select')?.value || 20;
        const mode = this.state.leaderboardMode;
        const domesticOnly = this.state.leaderboardPlayerFilter === 'domestic';
        
        // 如果是球队战绩榜模式，不执行球员排行榜刷新
        if (mode === 'team-standings') {
            return;
        }
        
        let response;
        if (mode === 'total') {
            // 总数据排行榜
            response = await this.apiGet(`/leaderboard/total/${statType}?min_games=${minGames}&top_n=${topN}&domestic_only=${domesticOnly}`);
        } else {
            // 常规赛或季后赛排行榜
            const isPlayoff = mode === 'playoff';
            response = await this.apiGet(`/leaderboard/${statType}?min_games=${minGames}&top_n=${topN}&is_playoff=${isPlayoff}&domestic_only=${domesticOnly}`);
        }
        
        if (!response.success) {
            this.showToast(response.error?.message || '加载排行榜失败', 'error');
            return;
        }
        
        const data = response.data;
        
        // 更新标题（根据模式添加前缀）
        const modePrefix = mode === 'playoff' ? '季后赛 ' : (mode === 'total' ? '总 ' : '');
        const playerFilterSuffix = domesticOnly ? ' (本土)' : '';
        const statNames = {
            'points': '🏀 得分榜',
            'rebounds': '📊 篮板榜',
            'assists': '🎯 助攻榜',
            'steals': '✋ 抢断榜',
            'blocks': '🖐️ 盖帽榜'
        };
        const statColumnNames = {
            'points': '场均得分',
            'rebounds': '场均篮板',
            'assists': '场均助攻',
            'steals': '场均抢断',
            'blocks': '场均盖帽'
        };
        
        document.getElementById('leaderboard-title').textContent = modePrefix + (statNames[statType] || statType) + playerFilterSuffix;
        document.getElementById('stat-column-header').textContent = statColumnNames[statType] || '数据';
        
        // 渲染表格
        const tbody = document.getElementById('leaderboard-body');
        const noData = document.getElementById('no-leaderboard-data');
        
        if (!data.leaderboard || data.leaderboard.length === 0) {
            tbody.innerHTML = '';
            if (noData) {
                if (mode === 'playoff') {
                    noData.textContent = '暂无季后赛数据，请等待季后赛比赛进行后查看';
                } else if (mode === 'total') {
                    noData.textContent = '暂无数据，请等待比赛进行后查看';
                } else {
                    noData.textContent = '暂无数据，请等待比赛进行后查看';
                }
                noData.classList.remove('hidden');
            }
            return;
        }
        
        noData?.classList.add('hidden');
        
        // 总数据模式显示额外的场次信息
        if (mode === 'total') {
            tbody.innerHTML = data.leaderboard.map((entry, index) => `
                <tr class="${entry.player_id === this.state.gameState?.player_team?.id ? 'text-primary' : ''}">
                    <td>
                        <span class="rank-badge ${index < 3 ? 'rank-top' : ''}">${entry.rank || index + 1}</span>
                    </td>
                    <td>
                        <span class="player-name" style="cursor: pointer;" onclick="GameApp.showPlayerDetail('${entry.player_id}')">
                            ${entry.player_name}
                        </span>
                        ${entry.is_foreign ? '<span class="foreign-badge">外援</span>' : ''}
                    </td>
                    <td>${entry.team_name}</td>
                    <td title="常规赛${entry.regular_games}场 + 季后赛${entry.playoff_games}场">${entry.games_played}</td>
                    <td><strong>${entry.stat_value.toFixed(1)}</strong></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = data.leaderboard.map((entry, index) => `
                <tr class="${entry.player_id === this.state.gameState?.player_team?.id ? 'text-primary' : ''}">
                    <td>
                        <span class="rank-badge ${index < 3 ? 'rank-top' : ''}">${entry.rank || index + 1}</span>
                    </td>
                    <td>
                        <span class="player-name" style="cursor: pointer;" onclick="GameApp.showPlayerDetail('${entry.player_id}')">
                            ${entry.player_name}
                        </span>
                        ${entry.is_foreign ? '<span class="foreign-badge">外援</span>' : ''}
                    </td>
                    <td>${entry.team_name}</td>
                    <td>${entry.games_played}</td>
                    <td><strong>${entry.stat_value.toFixed(1)}</strong></td>
                </tr>
            `).join('');
        }
    },

    // ============================================
    // 当日比赛系统
    // ============================================
    // 当日比赛系统 (Requirements 3.1, 3.2, 3.3)
    // ============================================
    async loadDailyGamesPage() {
        // 检查是否在季后赛阶段
        const state = this.state.gameState;
        if (state?.is_playoff_phase) {
            // 季后赛阶段显示季后赛对阵信息
            await this.loadPlayoffGamesPage();
            return;
        }
        
        // 设置日期为当前游戏日期
        const currentDate = state?.current_date;
        if (currentDate) {
            document.getElementById('daily-games-date').value = currentDate;
        }
        await this.loadDailyGames();
    },

    /**
     * 加载季后赛比赛页面
     * 在季后赛阶段，重定向到季后赛轮次比赛页面
     */
    async loadPlayoffGamesPage() {
        // 直接加载季后赛轮次比赛页面
        await this.loadPlayoffRoundGamesPage();
    },

    /**
     * 加载季后赛轮次比赛页面（含球员统计）
     * 类似于常规赛的每日比赛页面，但以轮次为单位
     */
    async loadPlayoffRoundGamesPage(roundName = null) {
        const container = document.getElementById('daily-games-list');
        const noGames = document.getElementById('no-daily-games');
        const summaryCard = document.getElementById('daily-games-summary');
        const datePickerCard = document.querySelector('#daily-games-page .card.mb-2');
        
        // 隐藏日期选择器
        if (datePickerCard) datePickerCard.style.display = 'none';
        noGames?.classList.add('hidden');
        
        // 如果没有指定轮次，获取当前轮次
        if (!roundName) {
            const bracketData = await this.loadPlayoffBracket();
            roundName = bracketData?.current_round || 'play_in';
        }
        
        // 保存当前选择的轮次
        this.state.currentPlayoffRound = roundName;
        
        // 更新摘要卡片为轮次选择器
        if (summaryCard) {
            summaryCard.classList.remove('hidden');
            const summaryContent = summaryCard.querySelector('.card-body');
            if (summaryContent) {
                summaryContent.innerHTML = `
                    <div class="playoff-round-selector" style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
                        <button class="btn ${roundName === 'play_in' ? 'btn-primary' : 'btn-outline'}" onclick="GameApp.loadPlayoffRoundGamesPage('play_in')">附加赛</button>
                        <button class="btn ${roundName === 'quarter' ? 'btn-primary' : 'btn-outline'}" onclick="GameApp.loadPlayoffRoundGamesPage('quarter')">四分之一决赛</button>
                        <button class="btn ${roundName === 'semi' ? 'btn-primary' : 'btn-outline'}" onclick="GameApp.loadPlayoffRoundGamesPage('semi')">半决赛</button>
                        <button class="btn ${roundName === 'final' ? 'btn-primary' : 'btn-outline'}" onclick="GameApp.loadPlayoffRoundGamesPage('final')">总决赛</button>
                    </div>
                `;
            }
        }
        
        // 加载指定轮次的比赛数据
        try {
            const response = await this.apiGet(`/playoff/round-games/${roundName}`);
            
            if (!response.success) {
                this.showToast(response.error?.message || '加载季后赛比赛数据失败', 'error');
                return;
            }
            
            const data = response.data;
            
            if (!data.series_list || data.series_list.length === 0) {
                container.innerHTML = `
                    <div class="card">
                        <div class="card-body text-center" style="padding: 50px;">
                            <div style="font-size: 3rem; margin-bottom: 15px;">📅</div>
                            <h3>该轮次暂无比赛</h3>
                            <p class="text-muted">请选择其他轮次查看比赛</p>
                        </div>
                    </div>
                `;
                return;
            }
            
            // 渲染轮次比赛列表
            container.innerHTML = this.renderPlayoffRoundGames(data);
            
        } catch (error) {
            console.error('Error loading playoff round games:', error);
            container.innerHTML = `
                <div class="card">
                    <div class="card-body text-center">
                        <p class="text-muted">加载季后赛比赛数据失败</p>
                    </div>
                </div>
            `;
        }
    },

    /**
     * 渲染季后赛轮次比赛列表
     */
    renderPlayoffRoundGames(data) {
        const playerTeamId = this.state.gameState?.player_team?.id;
        
        let html = `
            <div class="playoff-round-games">
                <div class="card mb-2">
                    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🏆 ${data.round_display_name}</span>
                        <span class="text-muted">${data.total_series} 组对阵</span>
                    </div>
                </div>
        `;
        
        // 渲染每个系列赛
        for (const series of data.series_list) {
            const isPlayerSeries = series.team1_id === playerTeamId || series.team2_id === playerTeamId;
            const seriesBorderStyle = isPlayerSeries ? 'border: 2px solid var(--primary-color);' : '';
            
            html += `
                <div class="game-card-enhanced" style="${seriesBorderStyle}">
                    <div class="series-header" style="padding: 15px 20px; background: linear-gradient(135deg, rgba(29, 53, 87, 0.05), rgba(69, 123, 157, 0.05)); border-bottom: 1px solid var(--border-color);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="display: flex; align-items: center; gap: 20px;">
                                <span style="font-weight: 600;">${series.team1_name}</span>
                                <span style="font-size: 1.5rem; font-weight: 800; color: var(--primary-color);">${series.team1_wins} - ${series.team2_wins}</span>
                                <span style="font-weight: 600;">${series.team2_name}</span>
                            </div>
                            <div>
                                ${series.is_complete ? 
                                    `<span class="game-status-badge status-finished">🏆 ${series.winner_name} 晋级</span>` : 
                                    `<span class="game-status-badge status-scheduled">进行中</span>`
                                }
                            </div>
                        </div>
                    </div>
            `;
            
            // 渲染系列赛中的每场比赛
            if (series.games && series.games.length > 0) {
                for (let i = 0; i < series.games.length; i++) {
                    const game = series.games[i];
                    const gameIndex = `${series.series_id}_${i}`;
                    const homeWinner = game.home_score > game.away_score;
                    const awayWinner = game.away_score > game.home_score;
                    
                    html += `
                        <div class="game-card-header-enhanced" onclick="GameApp.toggleGameDetails('${gameIndex}')" style="border-bottom: 1px solid var(--border-color);">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <span style="color: var(--text-secondary); font-size: 0.9rem;">G${game.game_number}</span>
                                <div class="game-matchup" style="display: flex; align-items: center; gap: 20px;">
                                    <div class="game-team-block" style="min-width: 120px;">
                                        <div class="game-team-name-enhanced" style="font-size: 1rem;">${game.home_team_name}</div>
                                        <div class="game-team-score ${homeWinner ? 'winner' : ''}" style="font-size: 1.8rem;">${game.home_score}</div>
                                    </div>
                                    <div class="game-vs-divider">
                                        <span class="vs-text-enhanced" style="font-size: 0.9rem;">VS</span>
                                    </div>
                                    <div class="game-team-block" style="min-width: 120px;">
                                        <div class="game-team-name-enhanced" style="font-size: 1rem;">${game.away_team_name}</div>
                                        <div class="game-team-score ${awayWinner ? 'winner' : ''}" style="font-size: 1.8rem;">${game.away_score}</div>
                                    </div>
                                </div>
                            </div>
                            <span class="expand-icon" id="expand-icon-${gameIndex}">▼</span>
                        </div>
                        <div class="game-details-enhanced" id="game-details-${gameIndex}">
                            ${this.renderPlayoffGameDetails(game)}
                        </div>
                    `;
                }
            } else {
                html += `
                    <div style="padding: 30px; text-align: center; color: var(--text-secondary);">
                        <div style="font-size: 2rem; margin-bottom: 10px;">⏳</div>
                        <div>该系列赛尚未开始</div>
                    </div>
                `;
            }
            
            html += '</div>';
        }
        
        html += '</div>';
        return html;
    },

    /**
     * 渲染季后赛单场比赛详情（球员统计）
     */
    renderPlayoffGameDetails(game) {
        const playerStats = game.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        return `
            <!-- 主队球员统计 -->
            <div class="team-stats-section">
                <div class="team-stats-header">
                    <div class="team-stats-title">
                        🏠 ${game.home_team_name} 球员数据
                    </div>
                    <div class="team-total-score">总分: ${game.home_score}</div>
                </div>
                <div class="table-container">
                    ${this.renderPlayerStatsTable(homeStats, 'home')}
                </div>
            </div>
            
            <!-- 客队球员统计 -->
            <div class="team-stats-section">
                <div class="team-stats-header">
                    <div class="team-stats-title">
                        ✈️ ${game.away_team_name} 球员数据
                    </div>
                    <div class="team-total-score">总分: ${game.away_score}</div>
                </div>
                <div class="table-container">
                    ${this.renderPlayerStatsTable(awayStats, 'away')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染季后赛对阵图到指定容器
     */
    renderPlayoffBracketToContainer(bracketData, container) {
        if (!bracketData || !bracketData.is_playoff_phase) {
            container.innerHTML = '<p class="text-muted text-center">季后赛尚未开始</p>';
            return;
        }
        
        const currentRound = bracketData.current_round || 'play_in';
        const playerTeamId = this.state.gameState?.player_team?.id;
        
        let html = `
            <div class="playoff-bracket-container">
                <div class="playoff-round-indicator" style="text-align: center; margin-bottom: 20px;">
                    当前轮次: <span class="current-round-name" style="font-weight: bold; color: var(--primary-color);">${this.getRoundDisplayName(currentRound)}</span>
                </div>
                
                <!-- 添加查看详细比赛数据按钮 -->
                <div style="text-align: center; margin-bottom: 20px;">
                    <button class="btn btn-primary" onclick="GameApp.showPage('playoff-round-games')">
                        📊 查看详细比赛数据
                    </button>
                </div>
        `;
        
        // 渲染各轮次
        const rounds = ['play_in', 'quarter', 'semi', 'final'];
        for (const round of rounds) {
            const seriesList = this.getSeriesForRound(bracketData.bracket, round);
            if (seriesList.length > 0) {
                html += `
                    <div class="playoff-round" style="margin-bottom: 20px;">
                        <h4 style="color: var(--secondary-color); margin-bottom: 10px;">${this.getRoundDisplayName(round)}</h4>
                        <div class="playoff-series-list">
                `;
                
                for (const series of seriesList) {
                    const isPlayerSeries = series.team1_id === playerTeamId || series.team2_id === playerTeamId;
                    const seriesClass = isPlayerSeries ? 'player-series' : '';
                    const team1Winner = series.is_complete && series.winner_id === series.team1_id;
                    const team2Winner = series.is_complete && series.winner_id === series.team2_id;
                    
                    html += `
                        <div class="playoff-series-card ${seriesClass}" style="background: var(--card-background); border-radius: 8px; padding: 15px; margin-bottom: 10px; border: ${isPlayerSeries ? '2px solid var(--primary-color)' : '1px solid var(--border-color)'};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1;">
                                    <div style="font-weight: ${team1Winner ? 'bold' : 'normal'}; color: ${team1Winner ? 'var(--success-color)' : 'inherit'};">
                                        ${series.team1_name} ${team1Winner ? '✓' : ''}
                                    </div>
                                    <div style="font-weight: ${team2Winner ? 'bold' : 'normal'}; color: ${team2Winner ? 'var(--success-color)' : 'inherit'};">
                                        ${series.team2_name} ${team2Winner ? '✓' : ''}
                                    </div>
                                </div>
                                <div style="text-align: center; min-width: 60px;">
                                    <div style="font-size: 1.2rem; font-weight: bold;">
                                        ${series.team1_wins} - ${series.team2_wins}
                                    </div>
                                    <div style="font-size: 0.8rem; color: var(--text-secondary);">
                                        ${series.is_complete ? '已结束' : '进行中'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                html += `
                        </div>
                    </div>
                `;
            }
        }
        
        // 显示冠军
        if (bracketData.champion_name) {
            html += `
                <div class="playoff-champion" style="text-align: center; padding: 20px; background: linear-gradient(135deg, #ffd700, #ffb700); border-radius: 12px; margin-top: 20px;">
                    <div style="font-size: 3rem;">🏆</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: var(--secondary-color);">
                        ${bracketData.champion_name}
                    </div>
                    <div style="color: var(--secondary-color);">总冠军</div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    },

    /**
     * 获取指定轮次的系列赛列表
     */
    getSeriesForRound(bracket, round) {
        const seriesList = [];
        if (!bracket) return seriesList;
        
        if (round === 'play_in') {
            for (let i = 1; i <= 4; i++) {
                const key = `play_in_${i}`;
                if (bracket[key]) seriesList.push(bracket[key]);
            }
        } else if (round === 'quarter') {
            for (let i = 1; i <= 4; i++) {
                const key = `quarter_${i}`;
                if (bracket[key]) seriesList.push(bracket[key]);
            }
        } else if (round === 'semi') {
            for (let i = 1; i <= 2; i++) {
                const key = `semi_${i}`;
                if (bracket[key]) seriesList.push(bracket[key]);
            }
        } else if (round === 'final') {
            if (bracket.final) seriesList.push(bracket.final);
        }
        
        return seriesList;
    },

    /**
     * 加载每日比赛数据 (Requirements 6.1, 6.2, 6.3, 6.4, 6.5)
     * 处理新的API响应格式，显示球队总分和完整球员统计
     */
    async loadDailyGames() {
        const date = document.getElementById('daily-games-date')?.value;
        if (!date) {
            this.showToast('请选择日期', 'warning');
            return;
        }
        
        const response = await this.apiGet(`/daily-games/${date}`);
        
        if (!response.success) {
            this.showToast(response.error?.message || '加载比赛数据失败', 'error');
            return;
        }
        
        const data = response.data;
        const container = document.getElementById('daily-games-list');
        const noGames = document.getElementById('no-daily-games');
        const summaryCard = document.getElementById('daily-games-summary');
        
        // 更新统计摘要 (Requirements 3.1)
        this.updateDailyGamesSummary(data);
        
        if (!data.games || data.games.length === 0) {
            container.innerHTML = '';
            noGames?.classList.remove('hidden');
            summaryCard?.classList.add('hidden');
            return;
        }
        
        noGames?.classList.add('hidden');
        summaryCard?.classList.remove('hidden');
        
        // 渲染增强版比赛卡片 (Requirements 3.1, 3.2)
        container.innerHTML = data.games.map((game, index) => this.renderDailyGameCard(game, index)).join('');
    },

    /**
     * 更新每日比赛统计摘要 (Requirements 3.1)
     */
    updateDailyGamesSummary(data) {
        const totalGames = data.total_games || (data.games ? data.games.length : 0);
        const playedGames = data.played_games || (data.games ? data.games.filter(g => g.is_played).length : 0);
        const scheduledGames = totalGames - playedGames;
        
        const totalEl = document.getElementById('total-games-count');
        const playedEl = document.getElementById('played-games-count');
        const scheduledEl = document.getElementById('scheduled-games-count');
        
        if (totalEl) totalEl.textContent = totalGames;
        if (playedEl) playedEl.textContent = playedGames;
        if (scheduledEl) scheduledEl.textContent = scheduledGames;
    },

    /**
     * 渲染增强版比赛卡片 (Requirements 6.1, 6.4, 6.5)
     * 显示球队总分和比赛状态，未开始比赛显示友好提示
     */
    renderDailyGameCard(game, index) {
        const statusClass = game.is_played ? 'status-finished' : 'status-scheduled';
        const statusText = game.is_played ? '已结束' : '未开始';
        
        // 判断获胜方 (Requirements 6.1)
        const homeWinner = game.is_played && game.home_score > game.away_score;
        const awayWinner = game.is_played && game.away_score > game.home_score;
        
        // 未开始比赛的友好提示 (Requirements 6.4)
        const notStartedMessage = `
            <div class="game-not-started-message">
                <div class="icon">⏰</div>
                <div class="title">比赛尚未开始</div>
                <div class="subtitle">请等待比赛开始后查看统计数据</div>
            </div>
        `;
        
        return `
            <div class="game-card-enhanced">
                <div class="game-card-header-enhanced" onclick="GameApp.toggleGameDetails(${index})">
                    <div class="game-matchup">
                        <div class="game-team-block">
                            <div class="game-team-name-enhanced">${game.home_team_name}</div>
                            <div class="game-team-score ${homeWinner ? 'winner' : ''}">${game.is_played ? game.home_score : '-'}</div>
                        </div>
                        <div class="game-vs-divider">
                            <span class="vs-text-enhanced">VS</span>
                        </div>
                        <div class="game-team-block">
                            <div class="game-team-name-enhanced">${game.away_team_name}</div>
                            <div class="game-team-score ${awayWinner ? 'winner' : ''}">${game.is_played ? game.away_score : '-'}</div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div class="game-status-badge ${statusClass}">${statusText}</div>
                        <span class="expand-icon" id="expand-icon-${index}">▼</span>
                    </div>
                </div>
                <div class="game-details-enhanced" id="game-details-${index}">
                    ${game.is_played ? this.renderGameDetails(game, index) : notStartedMessage}
                </div>
            </div>
        `;
    },

    /**
     * 渲染完整球员统计数据 (Requirements 6.1, 6.2, 6.3, 6.4)
     * 显示球队总分和每个球员的详细统计：得分、篮板、助攻、抢断、盖帽、失误
     */
    renderGameDetails(game, index) {
        const playerStats = game.player_stats || {};
        const homeStats = playerStats.home_team || [];
        const awayStats = playerStats.away_team || [];
        
        // 计算球队总分用于验证 (Requirements 6.1)
        const homeTeamPoints = homeStats.reduce((sum, p) => sum + (p.points || 0), 0);
        const awayTeamPoints = awayStats.reduce((sum, p) => sum + (p.points || 0), 0);
        
        return `
            <!-- 主队球员统计 (Requirements 6.2) -->
            <div class="team-stats-section">
                <div class="team-stats-header">
                    <div class="team-stats-title">
                        🏠 ${game.home_team_name} 球员数据
                    </div>
                    <div class="team-total-score">总分: ${game.home_score}</div>
                </div>
                <div class="table-container">
                    ${this.renderPlayerStatsTable(homeStats, 'home')}
                </div>
            </div>
            
            <!-- 客队球员统计 (Requirements 6.2) -->
            <div class="team-stats-section">
                <div class="team-stats-header">
                    <div class="team-stats-title">
                        ✈️ ${game.away_team_name} 球员数据
                    </div>
                    <div class="team-total-score">总分: ${game.away_score}</div>
                </div>
                <div class="table-container">
                    ${this.renderPlayerStatsTable(awayStats, 'away')}
                </div>
            </div>
        `;
    },

    /**
     * 渲染球员统计表格 (Requirements 6.2, 6.4)
     * 包含得分、篮板、助攻、抢断、盖帽、失误等完整统计
     * 当无数据时显示友好提示
     */
    renderPlayerStatsTable(playerStats, teamType) {
        if (!playerStats || playerStats.length === 0) {
            return `
                <div class="no-stats-message">
                    <div class="no-stats-message-icon">📊</div>
                    <div class="no-stats-message-title">暂无球员统计数据</div>
                    <div class="no-stats-message-text">该球队的球员数据尚未记录</div>
                </div>
            `;
        }
        
        // 按得分排序，高分球员在前
        const sortedStats = [...playerStats].sort((a, b) => (b.points || 0) - (a.points || 0));
        
        return `
            <table class="player-stats-table">
                <thead>
                    <tr>
                        <th>球员</th>
                        <th>得分</th>
                        <th>篮板</th>
                        <th>助攻</th>
                        <th>抢断</th>
                        <th>盖帽</th>
                        <th>失误</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedStats.map(p => this.renderPlayerStatRow(p)).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染单个球员统计行 (Requirements 6.2, 6.3)
     * 高亮显示优秀数据：20+得分、30+得分、10+篮板/助攻、5+抢断/盖帽
     */
    renderPlayerStatRow(player) {
        const points = player.points || 0;
        const rebounds = player.rebounds || 0;
        const assists = player.assists || 0;
        const steals = player.steals || 0;
        const blocks = player.blocks || 0;
        const turnovers = player.turnovers || 0;
        
        // 高亮样式：30+得分超级高亮，20+得分特别高亮，10+数据加粗
        let pointsClass = '';
        if (points >= 30) {
            pointsClass = 'stat-highlight points-30plus';
        } else if (points >= 20) {
            pointsClass = 'stat-highlight points-20plus';
        } else if (points >= 10) {
            pointsClass = 'stat-highlight';
        }
        
        const reboundsClass = rebounds >= 10 ? 'stat-highlight double-digit' : '';
        const assistsClass = assists >= 10 ? 'stat-highlight double-digit' : '';
        const stealsClass = steals >= 5 ? 'stat-highlight defensive-highlight' : '';
        const blocksClass = blocks >= 5 ? 'stat-highlight defensive-highlight' : '';
        
        return `
            <tr>
                <td>${player.player_name || '未知球员'}</td>
                <td><span class="${pointsClass}">${points}</span></td>
                <td><span class="${reboundsClass}">${rebounds}</span></td>
                <td><span class="${assistsClass}">${assists}</span></td>
                <td><span class="${stealsClass}">${steals}</span></td>
                <td><span class="${blocksClass}">${blocks}</span></td>
                <td>${turnovers}</td>
            </tr>
        `;
    },

    /**
     * 切换比赛详情展开/收起 (Requirements 3.1)
     */
    toggleGameDetails(index) {
        const details = document.getElementById(`game-details-${index}`);
        const expandIcon = document.getElementById(`expand-icon-${index}`);
        
        if (details) {
            const isExpanded = details.classList.contains('expanded');
            details.classList.toggle('expanded');
            
            if (expandIcon) {
                expandIcon.classList.toggle('expanded', !isExpanded);
            }
        }
    },

    changeDailyGamesDate(delta) {
        const dateInput = document.getElementById('daily-games-date');
        if (!dateInput?.value) return;
        
        const currentDate = new Date(dateInput.value);
        currentDate.setDate(currentDate.getDate() + delta);
        dateInput.value = currentDate.toISOString().split('T')[0];
        
        this.loadDailyGames();
    },

    loadDailyGamesToday() {
        const currentDate = this.state.gameState?.current_date;
        if (currentDate) {
            document.getElementById('daily-games-date').value = currentDate;
            this.loadDailyGames();
        }
    },

    // ============================================
    // 赛程页面
    // ============================================
    async loadSchedule() {
        const teamId = this.state.gameState?.player_team?.id;
        if (!teamId) return;
        
        const response = await this.apiGet(`/schedule?team_id=${teamId}`);
        if (!response.success) return;
        
        // 如果有赛程页面，渲染赛程
        const container = document.getElementById('schedule-list');
        if (container && response.data.schedule) {
            container.innerHTML = response.data.schedule.map(game => {
                const isHome = game.home_team_id === teamId;
                const opponent = isHome ? game.away_team_name : game.home_team_name;
                const result = game.is_played ? 
                    `${game.home_score} - ${game.away_score}` : '未进行';
                const resultClass = game.is_played ? 
                    ((isHome && game.home_score > game.away_score) || (!isHome && game.away_score > game.home_score) ? 'text-success' : 'text-danger') : '';
                
                return `
                    <div class="schedule-item">
                        <div class="schedule-date">${game.date}</div>
                        <div class="schedule-opponent">${isHome ? '主场' : '客场'} vs ${opponent}</div>
                        <div class="schedule-result ${resultClass}">${result}</div>
                    </div>
                `;
            }).join('');
        }
    }

};

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    GameApp.init();
});
