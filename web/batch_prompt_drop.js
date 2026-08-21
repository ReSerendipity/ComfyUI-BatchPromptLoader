(function() {
    // Wait for ComfyUI to be ready
    function initDragAndDrop() {
        const app = window.comfyApp;
        
        if (!app || !app.canvas) {
            setTimeout(initDragAndDrop, 100);
            return;
        }
        
        console.log('[BatchPromptLoader] Initializing drag and drop...');
        
        // Get the main canvas element
        const canvas = app.canvas.canvas;
        const container = canvas.closest('.graphcanvas');
        
        if (!container) {
            console.warn('[BatchPromptLoader] Container not found, retrying...');
            setTimeout(initDragAndDrop, 200);
            return;
        }
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            container.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        // Highlight drop area when dragging over
        let highlightTimeout;
        container.addEventListener('dragenter', () => {
            container.style.border = '3px dashed #4a90d9';
            highlightTimeout = setTimeout(() => {
                container.style.background = 'rgba(74, 144, 217, 0.1)';
            }, 100);
        });
        
        container.addEventListener('dragleave', () => {
            clearTimeout(highlightTimeout);
            container.style.border = '';
            container.style.background = '';
        });
        
        container.addEventListener('dragover', (e) => {
            e.dataTransfer.dropEffect = 'copy';
        });
        
        // Handle dropped files
        container.addEventListener('drop', async (e) => {
            clearTimeout(highlightTimeout);
            container.style.border = '';
            container.style.background = '';
            
            const files = e.dataTransfer.files;
            if (files.length === 0) return;
            
            // Filter for txt files
            const txtFiles = Array.from(files).filter(file => 
                file.name.toLowerCase().endsWith('.txt')
            );
            
            if (txtFiles.length === 0) {
                alert('⚠️ 请拖拽 TXT 文件！\n\n只支持 .txt 格式的提示词文件。');
                return;
            }
            
            try {
                // Show loading
                const originalTitle = document.title;
                document.title = `正在上传 ${txtFiles.length} 个文件...`;
                
                // Read all files
                const prompts = [];
                for (let file of txtFiles) {
                    const text = await file.text();
                    prompts.push({
                        name: file.name,
                        content: text
                    });
                }
                
                // Send to server via API
                const response = await fetch('/batchprompt/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        prompts: prompts,
                        target_dir: 'input/batch_temp'
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`上传失败：${response.status}`);
                }
                
                const result = await response.json();
                
                // Show success message
                alert(`✅ 成功上传 ${result.count} 个提示词文件！\n\n文件位置：${result.target_dir}\n\n现在可以修改"当前第几张"来批量生成了！`);
                
                document.title = originalTitle;
                
            } catch (error) {
                console.error('[BatchPromptLoader] Upload error:', error);
                alert(`❌ 上传失败\n\n错误信息：${error.message}\n\n请检查控制台获取详细信息。`);
            }
        });
        
        console.log('[BatchPromptLoader] Drag and drop initialized successfully!');
    }
    
    // Start initialization
    initDragAndDrop();
})();
