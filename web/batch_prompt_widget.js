// Batch Prompt Loader - Web Widget for file selection
(function() {
    const app = window.comfyApp;
    
    // Register custom widget for BatchPromptLoader
    const originalCreateGraphWidgets = LiteGraph.LGraphNode.prototype.createWidgets;
    LiteGraph.LGraphNode.prototype.createWidgets = function() {
        const result = originalCreateGraphWidgets.apply(this, arguments);
        
        if (this.type === "BatchPromptLoader") {
            // Add a button widget for file selection
            const uploadBtn = this.addWidget("button", "📁 选择提示词文件", null, () => {
                // Trigger file dialog via custom message
                app.ui.settings.addSetting({
                    id: "BatchPromptUpload",
                    name: "Batch Prompt Upload",
                    type: "custom",
                    render: (props) => React.createElement('div', null)
                });
                
                // Open file picker using ComfyUI's API
                const input = document.createElement('input');
                input.type = 'file';
                input.multiple = true;
                input.accept = '.txt';
                
                input.onchange = async (e) => {
                    const files = e.target.files;
                    if (files.length === 0) return;
                    
                    // Read all files
                    const prompts = [];
                    for (let file of files) {
                        const text = await file.text();
                        prompts.push({
                            filename: file.name,
                            content: text
                        });
                    }
                    
                    // Store in node data
                    this.prompts_data = prompts;
                    this.updateDisplay();
                    
                    // Queue prompt to refresh
                    app.queuePrompt(0);
                };
                
                input.click();
            });
            
            // Display widget to show loaded files count
            this.displayWidget = this.addWidget("text", "已加载：0 个文件", "", (val) => {}, {
                serialize: false
            });
            
            this.updateDisplay = function() {
                const count = this.prompts_data ? this.prompts_data.length : 0;
                this.displayWidget.value = `已加载：${count} 个文件`;
            };
        }
        
        return result;
    };
    
    // Override onExecuted to update display after execution
    const originalOnExecuted = LiteGraph.LGraphNode.prototype.onExecuted;
    LiteGraph.LGraphNode.prototype.onExecuted = function(message) {
        if (this.type === "BatchPromptLoader" && message.file_count !== undefined) {
            this.widgets.find(w => w.name === "已加载：0 个文件")?.setValue(`已加载：${message.file_count} 个文件`);
        }
        if (originalOnExecuted) {
            return originalOnExecuted.apply(this, arguments);
        }
    };
})();
