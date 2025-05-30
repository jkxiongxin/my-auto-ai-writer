// 全局变量
let currentTaskId = null;
let progressInterval = null;
const API_BASE_URL = 'http://localhost:8000';

// DOM元素
const elements = {
    navLinks: document.querySelectorAll('.nav-link'),
    sections: document.querySelectorAll('.section'),
    novelForm: document.getElementById('novelForm'),
    generateBtn: document.getElementById('generateBtn'),
    cancelBtn: document.getElementById('cancelBtn'),
    progressContainer: document.getElementById('generationProgress'),
    progressFill: document.querySelector('.progress-fill'),
    progressText: document.getElementById('progressText'),
    progressPercent: document.getElementById('progressPercent'),
    progressSteps: document.querySelectorAll('.step'),
    projectsList: document.getElementById('projectsList'),
    noProjects: document.getElementById('noProjects'),
    refreshProjects: document.getElementById('refreshProjects'),
    searchProjects: document.getElementById('searchProjects'),
    filterStatus: document.getElementById('filterStatus'),
    modal: document.getElementById('modal'),
    modalTitle: document.getElementById('modalTitle'),
    modalBody: document.getElementById('modalBody'),
    modalFooter: document.getElementById('modalFooter'),
    notifications: document.getElementById('notifications'),
    checkHealth: document.getElementById('checkHealth'),
    saveSettings: document.getElementById('saveSettings'),
    resetSettings: document.getElementById('resetSettings'),
    temperature: document.getElementById('temperature'),
    temperatureValue: document.getElementById('temperatureValue')
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    showSection('home');
    loadProjects();
    updateTemperatureDisplay();
    checkApiHealth();
}

function setupEventListeners() {
    // 导航链接
    elements.navLinks.forEach(link => {
        link.addEventListener('click', handleNavigation);
    });

    // 表单提交
    if (elements.novelForm) {
        elements.novelForm.addEventListener('submit', handleFormSubmit);
    }

    // 取消生成
    if (elements.cancelBtn) {
        elements.cancelBtn.addEventListener('click', cancelGeneration);
    }

    // 项目管理
    if (elements.refreshProjects) {
        elements.refreshProjects.addEventListener('click', loadProjects);
    }

    if (elements.searchProjects) {
        elements.searchProjects.addEventListener('input', filterProjects);
    }

    if (elements.filterStatus) {
        elements.filterStatus.addEventListener('change', filterProjects);
    }

    // 设置
    if (elements.checkHealth) {
        elements.checkHealth.addEventListener('click', checkApiHealth);
    }

    if (elements.saveSettings) {
        elements.saveSettings.addEventListener('click', saveSettings);
    }

    if (elements.resetSettings) {
        elements.resetSettings.addEventListener('click', resetSettings);
    }

    if (elements.temperature) {
        elements.temperature.addEventListener('input', updateTemperatureDisplay);
    }

    // 模态框关闭
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal-close') || e.target.classList.contains('modal')) {
            closeModal();
        }
    });

    // 键盘事件
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

// 导航处理
function handleNavigation(e) {
    e.preventDefault();
    const targetSection = e.target.closest('.nav-link').dataset.section;
    showSection(targetSection);
    
    // 更新活动导航链接
    elements.navLinks.forEach(link => link.classList.remove('active'));
    e.target.closest('.nav-link').classList.add('active');
}

function showSection(sectionName) {
    elements.sections.forEach(section => {
        section.classList.remove('active');
    });
    
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
        
        // 特殊处理
        if (sectionName === 'projects') {
            loadProjects();
        }
    }
}

// 表单提交处理
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(elements.novelForm);
    const requestData = {
        title: formData.get('title'),
        description: formData.get('description') || null,
        user_input: formData.get('userInput'),
        target_words: parseInt(formData.get('targetWords')),
        style_preference: formData.get('stylePreference') || null
    };

    // 表单验证
    if (!validateForm(requestData)) {
        return;
    }

    try {
        // 禁用表单
        setFormState(false);
        
        // 启动生成
        const response = await fetch(`${API_BASE_URL}/api/v1/generate-novel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        currentTaskId = result.task_id;

        // 显示进度界面
        showProgressInterface();
        
        // 开始监控进度
        startProgressMonitoring();
        
        showNotification('生成任务已启动', '正在为您创作精彩的小说...', 'success');

    } catch (error) {
        console.error('启动生成失败:', error);
        showNotification('启动失败', error.message, 'error');
        setFormState(true);
    }
}

function validateForm(data) {
    const errors = [];
    
    if (!data.title || data.title.trim().length < 1) {
        errors.push('请输入小说标题');
    }
    
    if (!data.user_input || data.user_input.trim().length < 10) {
        errors.push('创意描述至少需要10个字符');
    }
    
    if (!data.target_words || data.target_words < 1000 || data.target_words > 200000) {
        errors.push('目标字数必须在1000-200000之间');
    }

    if (errors.length > 0) {
        showNotification('表单验证失败', errors.join('<br>'), 'error');
        return false;
    }
    
    return true;
}

function setFormState(enabled) {
    const formElements = elements.novelForm.querySelectorAll('input, textarea, select, button');
    formElements.forEach(element => {
        element.disabled = !enabled;
    });
}

// 进度监控
function showProgressInterface() {
    elements.novelForm.style.display = 'none';
    elements.progressContainer.style.display = 'block';
    updateProgress(0, '正在初始化...');
}

function hideProgressInterface() {
    elements.novelForm.style.display = 'block';
    elements.progressContainer.style.display = 'none';
    setFormState(true);
}

function startProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(checkProgress, 2000);
    checkProgress(); // 立即检查一次
}

function stopProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

async function checkProgress() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/generate-novel/${currentTaskId}/status`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const status = await response.json();
        
        updateProgress(status.progress * 100, status.current_step || '处理中...');
        updateProgressSteps(status.current_step);

        if (status.status === 'completed') {
            stopProgressMonitoring();
            handleGenerationComplete();
        } else if (status.status === 'failed') {
            stopProgressMonitoring();
            handleGenerationError(status.error_message);
        } else if (status.status === 'cancelled') {
            stopProgressMonitoring();
            handleGenerationCancelled();
        }

    } catch (error) {
        console.error('检查进度失败:', error);
        // 继续监控，可能是临时网络问题
    }
}

function updateProgress(percent, stepText) {
    if (elements.progressFill) {
        elements.progressFill.style.width = `${percent}%`;
    }
    
    if (elements.progressPercent) {
        elements.progressPercent.textContent = `${Math.round(percent)}%`;
    }
    
    if (elements.progressText) {
        elements.progressText.textContent = stepText;
    }
}

function updateProgressSteps(currentStep) {
    const stepMap = {
        '初始化': 0,
        '概念扩展': 1,
        '策略选择': 2,
        '大纲生成': 3,
        '角色创建': 4,
        '章节生成': 5,
        '质量检查': 6
    };
    
    const currentIndex = stepMap[currentStep] || 0;
    
    elements.progressSteps.forEach((step, index) => {
        step.classList.remove('active', 'completed');
        
        if (index < currentIndex) {
            step.classList.add('completed');
        } else if (index === currentIndex) {
            step.classList.add('active');
        }
    });
}

async function handleGenerationComplete() {
    try {
        // 获取生成结果
        const response = await fetch(`${API_BASE_URL}/api/v1/generate-novel/${currentTaskId}/result`);
        const result = await response.json();
        
        hideProgressInterface();
        showGenerationResult(result);
        loadProjects(); // 刷新项目列表
        
        showNotification('生成完成', `小说《${result.title}》已成功生成！`, 'success');
        
    } catch (error) {
        console.error('获取生成结果失败:', error);
        showNotification('获取结果失败', error.message, 'error');
    }
    
    currentTaskId = null;
}

function handleGenerationError(errorMessage) {
    hideProgressInterface();
    showNotification('生成失败', errorMessage || '生成过程中发生未知错误', 'error');
    currentTaskId = null;
}

function handleGenerationCancelled() {
    hideProgressInterface();
    showNotification('已取消', '生成任务已被取消', 'warning');
    currentTaskId = null;
}

async function cancelGeneration() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/generate-novel/${currentTaskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            stopProgressMonitoring();
            handleGenerationCancelled();
        }

    } catch (error) {
        console.error('取消生成失败:', error);
        showNotification('取消失败', error.message, 'error');
    }
}

// 项目管理
async function loadProjects() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/projects`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        displayProjects(data.projects || []);

    } catch (error) {
        console.error('加载项目失败:', error);
        showNotification('加载失败', '无法加载项目列表', 'error');
        displayProjects([]);
    }
}

function displayProjects(projects) {
    if (!elements.projectsList) return;

    if (projects.length === 0) {
        elements.projectsList.style.display = 'none';
        elements.noProjects.style.display = 'block';
        return;
    }

    elements.projectsList.style.display = 'grid';
    elements.noProjects.style.display = 'none';

    elements.projectsList.innerHTML = projects.map(project => createProjectCard(project)).join('');
    
    // 添加事件监听器
    attachProjectCardListeners();
}

function createProjectCard(project) {
    const statusClass = `status-${project.status}`;
    const statusText = getStatusText(project.status);
    const createdDate = new Date(project.created_at).toLocaleDateString('zh-CN');
    
    return `
        <div class="project-card" data-project-id="${project.id}">
            <div class="project-header">
                <div>
                    <div class="project-title">${escapeHtml(project.title)}</div>
                    <div class="project-status ${statusClass}">${statusText}</div>
                </div>
            </div>
            <div class="project-info">
                <p><i class="fas fa-font"></i> 目标字数: ${project.target_words.toLocaleString()}</p>
                <p><i class="fas fa-calendar"></i> 创建时间: ${createdDate}</p>
                ${project.current_words ? `<p><i class="fas fa-file-alt"></i> 当前字数: ${project.current_words.toLocaleString()}</p>` : ''}
                ${project.description ? `<p><i class="fas fa-info-circle"></i> ${escapeHtml(project.description)}</p>` : ''}
            </div>
            <div class="project-actions">
                ${project.status === 'completed' ? `
                    <button class="btn btn-primary" onclick="viewProject(${project.id})">
                        <i class="fas fa-eye"></i> 查看
                    </button>
                    <button class="btn btn-secondary" onclick="exportProject(${project.id})">
                        <i class="fas fa-download"></i> 导出
                    </button>
                    <button class="btn btn-danger" onclick="deleteProject(${project.id}, true)" title="删除已完成的小说">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                ` : project.status === 'running' ? `
                    <button class="btn btn-secondary" onclick="viewProgress('${project.task_id}')">
                        <i class="fas fa-chart-line"></i> 进度
                    </button>
                ` : `
                    <button class="btn btn-danger" onclick="deleteProject(${project.id}, false)">
                        <i class="fas fa-trash"></i> 删除
                    </button>
                `}
            </div>
        </div>
    `;
}

function attachProjectCardListeners() {
    // 项目卡片已通过onclick属性绑定事件
}

function getStatusText(status) {
    const statusMap = {
        'queued': '排队中',
        'running': '生成中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
    };
    return statusMap[status] || status;
}

function filterProjects() {
    const searchTerm = elements.searchProjects.value.toLowerCase();
    const statusFilter = elements.filterStatus.value;
    
    const projectCards = elements.projectsList.querySelectorAll('.project-card');
    
    projectCards.forEach(card => {
        const title = card.querySelector('.project-title').textContent.toLowerCase();
        const status = card.querySelector('.project-status').classList[1].replace('status-', '');
        
        const matchesSearch = !searchTerm || title.includes(searchTerm);
        const matchesStatus = !statusFilter || status === statusFilter;
        
        card.style.display = matchesSearch && matchesStatus ? 'block' : 'none';
    });
}

// 项目操作
async function viewProject(projectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`);
        const project = await response.json();
        
        showModal('项目详情', `
            <h3>${escapeHtml(project.title)}</h3>
            <p><strong>状态:</strong> ${getStatusText(project.status)}</p>
            <p><strong>目标字数:</strong> ${project.target_words.toLocaleString()}</p>
            <p><strong>当前字数:</strong> ${(project.current_words || 0).toLocaleString()}</p>
            <p><strong>创建时间:</strong> ${new Date(project.created_at).toLocaleString('zh-CN')}</p>
            ${project.description ? `<p><strong>描述:</strong> ${escapeHtml(project.description)}</p>` : ''}
            <div style="margin-top: 1rem;">
                <button class="btn btn-primary" onclick="exportProject(${projectId}); closeModal();">
                    <i class="fas fa-download"></i> 导出内容
                </button>
            </div>
        `);
        
    } catch (error) {
        showNotification('查看失败', '无法获取项目详情', 'error');
    }
}

async function exportProject(projectId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}/export?format=txt`);
        
        if (!response.ok) {
            throw new Error('导出失败');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `novel_${projectId}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('导出成功', '文件已下载到本地', 'success');
        
    } catch (error) {
        showNotification('导出失败', error.message, 'error');
    }
}

async function deleteProject(projectId, isCompleted = false) {
    // 根据项目状态显示不同的确认消息
    let confirmMessage;
    if (isCompleted) {
        confirmMessage = `⚠️ 警告：您即将删除一个已完成的小说项目！

这将永久删除：
• 小说的所有章节内容
• 角色档案和设定
• 大纲和创作记录
• 质量评估报告

此操作无法撤销！确定要继续吗？

建议：删除前请先导出小说内容作为备份。`;
    } else {
        confirmMessage = '确定要删除这个项目吗？此操作无法撤销。';
    }

    if (!confirm(confirmMessage)) {
        return;
    }

    // 对于已完成的项目，要求二次确认
    if (isCompleted) {
        const secondConfirm = prompt('请输入 "确认删除" 来最终确认删除操作：');
        if (secondConfirm !== '确认删除') {
            showNotification('取消删除', '删除操作已取消', 'info');
            return;
        }
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/projects/${projectId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadProjects();
            const messageType = isCompleted ? '已完成的小说项目已删除' : '项目已删除';
            showNotification('删除成功', messageType, 'success');
        } else {
            const errorData = await response.json().catch(() => ({ detail: '删除失败' }));
            throw new Error(errorData.detail || '删除失败');
        }

    } catch (error) {
        showNotification('删除失败', error.message, 'error');
    }
}

async function viewProgress(taskId) {
    currentTaskId = taskId;
    showSection('generate');
    showProgressInterface();
    startProgressMonitoring();
}

// 设置管理
function updateTemperatureDisplay() {
    if (elements.temperature && elements.temperatureValue) {
        elements.temperatureValue.textContent = elements.temperature.value;
    }
}

async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const health = await response.json();
        
        showNotification('健康检查', `API服务状态: ${health.status}`, 'success');
        
    } catch (error) {
        showNotification('健康检查失败', '无法连接到API服务', 'error');
    }
}

function saveSettings() {
    // 这里可以实现设置保存逻辑
    showNotification('设置已保存', '您的设置已成功保存', 'success');
}

function resetSettings() {
    if (confirm('确定要重置所有设置为默认值吗？')) {
        // 重置表单值
        if (elements.temperature) {
            elements.temperature.value = 0.7;
            updateTemperatureDisplay();
        }
        
        showNotification('设置已重置', '所有设置已恢复为默认值', 'success');
    }
}

// 工具函数
function showModal(title, content, footer = '') {
    elements.modalTitle.textContent = title;
    elements.modalBody.innerHTML = content;
    if (footer) {
        elements.modalFooter.innerHTML = footer;
    }
    elements.modal.style.display = 'block';
}

function closeModal() {
    elements.modal.style.display = 'none';
}

function showNotification(title, message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-title">${escapeHtml(title)}</div>
        <div class="notification-message">${message}</div>
    `;
    
    elements.notifications.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function showGenerationResult(result) {
    showModal('生成完成', `
        <div style="text-align: center; margin-bottom: 1rem;">
            <i class="fas fa-check-circle" style="color: #27ae60; font-size: 3rem;"></i>
        </div>
        <h3 style="text-align: center; margin-bottom: 1rem;">《${escapeHtml(result.title)}》</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div><strong>总字数:</strong> ${result.total_words.toLocaleString()}</div>
            <div><strong>章节数:</strong> ${result.chapter_count}</div>
            <div><strong>质量评分:</strong> ${result.quality_score ? result.quality_score.toFixed(1) : 'N/A'}</div>
            <div><strong>生成时间:</strong> ${result.generation_time_seconds ? Math.round(result.generation_time_seconds) + '秒' : 'N/A'}</div>
        </div>
        <div style="text-align: center; margin-top: 2rem;">
            <button class="btn btn-primary" onclick="viewProject(${result.project_id}); closeModal();">
                <i class="fas fa-eye"></i> 查看详情
            </button>
            <button class="btn btn-secondary" onclick="exportProject(${result.project_id}); closeModal();" style="margin-left: 1rem;">
                <i class="fas fa-download"></i> 导出小说
            </button>
        </div>
    `);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 错误处理
window.addEventListener('error', function(e) {
    console.error('JavaScript错误:', e.error);
    showNotification('系统错误', '发生了意外错误，请刷新页面重试', 'error');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('未处理的Promise拒绝:', e.reason);
    showNotification('系统错误', '发生了意外错误，请刷新页面重试', 'error');
});