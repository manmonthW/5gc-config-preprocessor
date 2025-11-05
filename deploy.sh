#!/bin/bash

# 5GC配置预处理模块自动化部署脚本
# 支持Linux/Mac系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 检查Python版本
check_python() {
    print_info "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 7 ]; then
            print_info "Python版本: $PYTHON_VERSION ✓"
            PYTHON_CMD="python3"
        else
            print_error "Python版本过低，需要3.7或更高版本"
            exit 1
        fi
    else
        print_error "未找到Python3，请先安装Python 3.7+"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建Python虚拟环境..."
    
    if [ -d "venv" ]; then
        print_warning "虚拟环境已存在，是否重新创建？(y/n)"
        read -r response
        if [ "$response" = "y" ]; then
            rm -rf venv
            $PYTHON_CMD -m venv venv
            print_info "虚拟环境已重新创建"
        else
            print_info "使用现有虚拟环境"
        fi
    else
        $PYTHON_CMD -m venv venv
        print_info "虚拟环境创建成功"
    fi
}

# 激活虚拟环境并安装依赖
install_dependencies() {
    print_info "安装Python依赖包..."
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_info "依赖安装完成"
    else
        print_error "未找到requirements.txt文件"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录结构..."
    
    directories=(
        "output"
        "logs"
        "temp"
        "data/samples"
        "data/processed"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_info "创建目录: $dir"
    done
}

# 配置环境变量
setup_environment() {
    print_info "设置环境变量..."
    
    # 创建.env文件
    cat > .env << EOF
# 5GC配置预处理模块环境变量
PROJECT_ROOT=$(pwd)
CONFIG_FILE=config.yaml
LOG_LEVEL=INFO
OUTPUT_DIR=./output
TEMP_DIR=./temp
MAX_WORKERS=4
EOF
    
    print_info "环境变量配置完成"
}

# 运行测试
run_tests() {
    print_info "运行单元测试..."
    
    source venv/bin/activate
    
    if [ -f "tests/test_all.py" ]; then
        python tests/test_all.py
        if [ $? -eq 0 ]; then
            print_info "所有测试通过 ✓"
        else
            print_error "测试失败，请检查错误"
            exit 1
        fi
    else
        print_warning "未找到测试文件，跳过测试"
    fi
}

# 创建示例配置
create_sample_config() {
    print_info "创建示例配置文件..."
    
    source venv/bin/activate
    
    python quick_start.py --create-sample
    
    if [ $? -eq 0 ]; then
        print_info "示例配置创建成功"
    else
        print_error "创建示例配置失败"
    fi
}

# 设置系统服务（可选）
setup_service() {
    print_info "是否设置为系统服务？(y/n)"
    read -r response
    
    if [ "$response" = "y" ]; then
        print_info "创建systemd服务文件..."
        
        sudo cat > /etc/systemd/system/config-preprocessor.service << EOF
[Unit]
Description=5GC Config Preprocessor Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python $(pwd)/src/preprocessor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        print_info "系统服务已创建"
        print_info "启动服务: sudo systemctl start config-preprocessor"
        print_info "开机自启: sudo systemctl enable config-preprocessor"
    fi
}

# 创建快捷命令
create_shortcuts() {
    print_info "创建快捷命令..."
    
    # 创建可执行脚本
    cat > process-config << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
source venv/bin/activate
python quick_start.py "$@"
EOF
    
    chmod +x process-config
    
    print_info "快捷命令创建完成"
    print_info "使用方法: ./process-config -i your_config.txt"
}

# 显示部署信息
show_info() {
    cat << EOF

${GREEN}========================================${NC}
${GREEN}    5GC配置预处理模块部署成功！        ${NC}
${GREEN}========================================${NC}

部署信息:
- Python版本: $PYTHON_VERSION
- 项目路径: $(pwd)
- 虚拟环境: $(pwd)/venv
- 配置文件: config.yaml

快速使用:
1. 激活环境: source venv/bin/activate
2. 处理文件: python quick_start.py -i sample_5gc_config.txt
3. 查看帮助: python quick_start.py --help

或使用快捷命令:
./process-config -i your_config.txt

文档和示例:
- README.md - 详细使用说明
- sample_5gc_config.txt - 示例配置文件
- config.yaml - 模块配置

EOF
}

# 主函数
main() {
    print_info "开始部署5GC配置预处理模块..."
    echo ""
    
    # 执行部署步骤
    check_python
    create_venv
    install_dependencies
    create_directories
    setup_environment
    run_tests
    create_sample_config
    create_shortcuts
    setup_service
    
    # 显示部署信息
    show_info
    
    print_info "部署完成！"
}

# 错误处理
trap 'print_error "部署过程中发生错误，请检查日志"' ERR

# 执行主函数
main
