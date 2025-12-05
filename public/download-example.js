/**
 * 5GC Config Preprocessor - Vercel 环境前端下载示例
 *
 * 使用方法：
 * 1. 上传文件并发送 POST 请求到 /api
 * 2. 接收 JSON 响应（包含 base64 编码的文件）
 * 3. 触发浏览器下载
 */

/**
 * 方法1: 完整示例 - 上传文件并下载处理结果
 */
async function uploadAndProcessFile(file) {
    try {
        // 1. 读取文件为 base64
        const base64Content = await fileToBase64(file);

        // 2. 准备请求数据
        const requestData = {
            file_content: base64Content,
            filename: file.name,
            options: {
                desensitize: true,        // 脱敏
                convert_format: true,     // 格式转换
                chunk: false,             // 分块（可选）
                extract_metadata: true    // 元数据提取
            }
        };

        // 3. 发送 POST 请求
        const response = await fetch('/api', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // 4. 解析响应
        const result = await response.json();

        if (result.success) {
            // 5. 下载文件
            downloadFile(result.content_base64, result.filename);

            console.log('✅ 处理成功！');
            console.log(`📁 输出文件: ${result.filename}`);
            console.log(`📊 文件数量: ${result.file_count}`);
            console.log(`⏱️ 处理时间: ${result.processing_time}秒`);

            return result;
        } else {
            throw new Error(result.error || '处理失败');
        }

    } catch (error) {
        console.error('❌ 错误:', error);
        throw error;
    }
}

/**
 * 方法2: 从响应下载文件（核心逻辑）
 *
 * @param {string} base64Content - Base64 编码的文件内容
 * @param {string} filename - 文件名
 */
function downloadFile(base64Content, filename) {
    // 创建下载链接
    const link = document.createElement('a');
    link.href = 'data:application/octet-stream;base64,' + base64Content;
    link.download = filename;

    // 触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 方法3: 文件转 Base64
 *
 * @param {File} file - 文件对象
 * @returns {Promise<string>} Base64 字符串
 */
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = () => {
            // 移除 data URL 前缀，只保留 base64 内容
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };

        reader.onerror = (error) => {
            reject(error);
        };

        reader.readAsDataURL(file);
    });
}

/**
 * 方法4: 使用示例 - HTML 文件输入
 */
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');

    fileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];

        if (file) {
            console.log(`📄 选中文件: ${file.name}`);
            console.log(`📏 文件大小: ${formatFileSize(file.size)}`);

            try {
                await uploadAndProcessFile(file);
            } catch (error) {
                alert(`处理失败: ${error.message}`);
            }
        }
    });
}

/**
 * 方法5: 拖拽上传
 */
function setupDragAndDrop(dropAreaId) {
    const dropArea = document.getElementById(dropAreaId);

    // 阻止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // 高亮拖拽区域
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.add('highlight');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.remove('highlight');
        }, false);
    });

    // 处理文件拖放
    dropArea.addEventListener('drop', async (e) => {
        const files = e.dataTransfer.files;

        if (files.length > 0) {
            const file = files[0];
            try {
                await uploadAndProcessFile(file);
            } catch (error) {
                alert(`处理失败: ${error.message}`);
            }
        }
    }, false);
}

/**
 * 工具函数: 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

/**
 * 方法6: React 示例
 */
function ReactExample() {
    // React 组件示例
    const [processing, setProcessing] = React.useState(false);
    const [result, setResult] = React.useState(null);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setProcessing(true);

        try {
            const result = await uploadAndProcessFile(file);
            setResult(result);
            alert('处理成功！文件已下载');
        } catch (error) {
            alert(`错误: ${error.message}`);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div>
            <input
                type="file"
                onChange={handleFileUpload}
                disabled={processing}
                accept=".xml,.yaml,.yml,.json,.ini,.txt"
            />
            {processing && <p>处理中...</p>}
            {result && (
                <div>
                    <p>✅ 成功！文件: {result.filename}</p>
                    <p>处理时间: {result.processing_time}秒</p>
                </div>
            )}
        </div>
    );
}

/**
 * 方法7: Vue 示例
 */
const VueExample = {
    data() {
        return {
            processing: false,
            result: null
        };
    },
    methods: {
        async handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;

            this.processing = true;

            try {
                this.result = await uploadAndProcessFile(file);
                alert('处理成功！文件已下载');
            } catch (error) {
                alert(`错误: ${error.message}`);
            } finally {
                this.processing = false;
            }
        }
    },
    template: `
        <div>
            <input
                type="file"
                @change="handleFileUpload"
                :disabled="processing"
                accept=".xml,.yaml,.yml,.json,.ini,.txt"
            />
            <p v-if="processing">处理中...</p>
            <div v-if="result">
                <p>✅ 成功！文件: {{ result.filename }}</p>
                <p>处理时间: {{ result.processing_time }}秒</p>
            </div>
        </div>
    `
};

/**
 * 方法8: 直接从 URL 下载（如果有 base64 响应）
 */
function downloadFromResponse(response) {
    if (response.success && response.content_base64) {
        downloadFile(response.content_base64, response.filename);
        return true;
    }
    return false;
}

/**
 * 方法9: 批量下载（如果返回多个文件）
 */
function downloadMultipleFiles(filesArray) {
    filesArray.forEach((fileData, index) => {
        setTimeout(() => {
            downloadFile(fileData.content_base64, fileData.filename);
        }, index * 100); // 延迟下载，避免浏览器阻止
    });
}

/**
 * 方法10: 显示进度
 */
async function uploadWithProgress(file, onProgress) {
    const base64Content = await fileToBase64(file);

    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                onProgress(percentComplete);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                resolve(result);
            } else {
                reject(new Error(`HTTP ${xhr.status}`));
            }
        });

        xhr.addEventListener('error', () => {
            reject(new Error('Network error'));
        });

        xhr.open('POST', '/api');
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({
            file_content: base64Content,
            filename: file.name,
            options: {
                desensitize: true,
                convert_format: true,
                chunk: false,
                extract_metadata: true
            }
        }));
    });
}

// ==================== 导出（如果使用模块系统）====================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        uploadAndProcessFile,
        downloadFile,
        fileToBase64,
        formatFileSize,
        setupFileInput,
        setupDragAndDrop,
        downloadFromResponse,
        downloadMultipleFiles,
        uploadWithProgress
    };
}

// ==================== 示例使用 ====================

/*
// HTML:
<input type="file" id="fileInput" accept=".xml,.yaml,.json,.ini,.txt">
<div id="dropArea">拖拽文件到这里</div>

// JavaScript:
// 方式1: 文件输入
setupFileInput();

// 方式2: 拖拽上传
setupDragAndDrop('dropArea');

// 方式3: 手动调用
document.getElementById('fileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const result = await uploadAndProcessFile(file);
        console.log('完成!', result);
    }
});
*/
