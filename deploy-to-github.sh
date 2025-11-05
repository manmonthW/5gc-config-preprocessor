#!/bin/bash

# 5GC Config Preprocessor - GitHub部署脚本
# 自动化GitHub仓库初始化和部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 函数：打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Git是否安装
check_git() {
    if ! command_exists git; then
        print_error "Git未安装，请先安装Git"
        exit 1
    fi
    print_success "Git已安装: $(git --version)"
}

# 检查GitHub CLI是否安装
check_gh_cli() {
    if ! command_exists gh; then
        print_warning "GitHub CLI未安装，某些功能可能无法使用"
        print_info "安装GitHub CLI: https://cli.github.com/"
        return 1
    fi
    print_success "GitHub CLI已安装: $(gh --version | head -n 1)"
    return 0
}

# 初始化Git仓库
init_git_repo() {
    print_info "初始化Git仓库..."
    
    if [ -d .git ]; then
        print_warning "Git仓库已存在"
    else
        git init
        print_success "Git仓库初始化完成"
    fi
    
    # 设置Git用户信息
    if [ -z "$(git config user.name)" ]; then
        read -p "请输入Git用户名: " git_username
        git config user.name "$git_username"
    fi
    
    if [ -z "$(git config user.email)" ]; then
        read -p "请输入Git邮箱: " git_email
        git config user.email "$git_email"
    fi
    
    print_success "Git配置完成"
}

# 创建初始提交
create_initial_commit() {
    print_info "创建初始提交..."
    
    # 添加所有文件
    git add -A
    
    # 创建提交
    git commit -m "Initial commit: 5GC Config Preprocessor v1.0.0

- Core modules: desensitizer, format converter, chunker, metadata extractor
- Complete test suite
- Docker support
- CI/CD pipeline
- Comprehensive documentation" || true
    
    print_success "初始提交创建完成"
}

# 创建GitHub仓库
create_github_repo() {
    print_info "创建GitHub仓库..."
    
    if ! command_exists gh; then
        print_warning "GitHub CLI未安装，请手动创建仓库"
        print_info "访问: https://github.com/new"
        print_info "仓库名建议: 5gc-config-preprocessor"
        read -p "请输入GitHub仓库URL (格式: https://github.com/username/repo.git): " repo_url
    else
        # 使用GitHub CLI创建仓库
        read -p "请输入仓库名称 (默认: 5gc-config-preprocessor): " repo_name
        repo_name=${repo_name:-5gc-config-preprocessor}
        
        read -p "是否创建为私有仓库? (y/n, 默认: n): " is_private
        private_flag=""
        if [ "$is_private" = "y" ]; then
            private_flag="--private"
        else
            private_flag="--public"
        fi
        
        print_info "创建GitHub仓库: $repo_name"
        gh repo create "$repo_name" \
            --description "A comprehensive preprocessing tool for 5G Core Network configuration files" \
            --homepage "https://github.com/$USER/$repo_name" \
            $private_flag \
            --confirm
        
        repo_url="https://github.com/$USER/$repo_name.git"
        print_success "GitHub仓库创建成功"
    fi
    
    # 添加远程仓库
    if git remote get-url origin >/dev/null 2>&1; then
        print_warning "远程仓库origin已存在"
        git remote set-url origin "$repo_url"
    else
        git remote add origin "$repo_url"
    fi
    
    print_success "远程仓库配置完成: $repo_url"
}

# 推送代码到GitHub
push_to_github() {
    print_info "推送代码到GitHub..."
    
    # 设置默认分支为main
    git branch -M main
    
    # 推送代码
    git push -u origin main
    
    print_success "代码推送完成"
}

# 设置GitHub Pages
setup_github_pages() {
    print_info "设置GitHub Pages..."
    
    if command_exists gh; then
        gh repo edit --enable-wiki --enable-issues --enable-projects
        
        # 启用GitHub Pages
        print_info "启用GitHub Pages用于文档..."
        gh api repos/:owner/:repo/pages \
            --method POST \
            --field source='{"branch":"gh-pages","path":"/"}' \
            2>/dev/null || print_warning "GitHub Pages可能已启用或需要手动设置"
    else
        print_warning "请手动在GitHub仓库设置中启用GitHub Pages"
        print_info "Settings -> Pages -> Source: Deploy from a branch"
        print_info "Branch: gh-pages, Folder: / (root)"
    fi
}

# 创建GitHub Secrets
setup_github_secrets() {
    print_info "设置GitHub Secrets..."
    
    if command_exists gh; then
        print_info "配置GitHub Actions所需的Secrets"
        
        read -p "是否配置Docker Hub? (y/n): " setup_docker
        if [ "$setup_docker" = "y" ]; then
            read -p "Docker Hub用户名: " docker_username
            read -s -p "Docker Hub密码: " docker_password
            echo
            gh secret set DOCKER_USERNAME --body "$docker_username"
            gh secret set DOCKER_PASSWORD --body "$docker_password"
            print_success "Docker Hub配置完成"
        fi
        
        read -p "是否配置PyPI? (y/n): " setup_pypi
        if [ "$setup_pypi" = "y" ]; then
            read -s -p "PyPI API Token: " pypi_token
            echo
            gh secret set PYPI_API_TOKEN --body "$pypi_token"
            print_success "PyPI配置完成"
        fi
    else
        print_warning "请手动配置GitHub Secrets:"
        print_info "Settings -> Secrets and variables -> Actions"
        print_info "需要配置的Secrets:"
        print_info "  - DOCKER_USERNAME (可选)"
        print_info "  - DOCKER_PASSWORD (可选)"
        print_info "  - PYPI_API_TOKEN (可选)"
    fi
}

# 创建首个Release
create_release() {
    print_info "创建首个Release..."
    
    if command_exists gh; then
        # 创建tag
        git tag -a v1.0.0 -m "Initial Release v1.0.0

Features:
- Intelligent desensitization for sensitive data
- Multi-format support (XML, JSON, YAML, INI, Text)
- Smart chunking for large files
- 5GC-specific metadata extraction
- Docker support
- Complete test suite"
        
        git push origin v1.0.0
        
        # 创建Release
        gh release create v1.0.0 \
            --title "5GC Config Preprocessor v1.0.0" \
            --notes "Initial release of 5GC Config Preprocessor

## Features
- 🔒 Intelligent desensitization
- 🔄 Format conversion
- ✂️ Smart chunking
- 📊 Metadata extraction
- 🐳 Docker support
- ✅ Complete test suite

## Installation
\`\`\`bash
pip install 5gc-config-preprocessor
\`\`\`

## Docker
\`\`\`bash
docker pull ghcr.io/yourusername/5gc-config-preprocessor:v1.0.0
\`\`\`

See README for detailed usage instructions." \
            --draft
        
        print_success "Release草稿创建成功，请在GitHub上发布"
    else
        print_warning "请手动创建Release:"
        print_info "1. 访问: https://github.com/yourusername/repo/releases/new"
        print_info "2. Tag: v1.0.0"
        print_info "3. Title: 5GC Config Preprocessor v1.0.0"
    fi
}

# 显示部署后的信息
show_deployment_info() {
    cat << EOF

${GREEN}========================================${NC}
${GREEN}    GitHub部署成功完成！               ${NC}
${GREEN}========================================${NC}

📦 仓库信息:
- URL: $repo_url
- 分支: main
- 版本: v1.0.0

🔧 GitHub Actions:
- CI/CD Pipeline已配置
- 自动测试、构建、部署

📚 文档:
- GitHub Pages将自动部署
- 访问: https://yourusername.github.io/5gc-config-preprocessor/

🚀 下一步操作:
1. 访问GitHub仓库查看Actions运行状态
2. 配置额外的Secrets（如需要）
3. 发布Release（如已创建草稿）
4. 邀请协作者

📝 常用命令:
- 查看仓库: gh repo view --web
- 查看Actions: gh run list
- 查看Issues: gh issue list

⭐ 别忘了给仓库加Star！

EOF
}

# 主函数
main() {
    print_info "开始GitHub部署流程..."
    echo ""
    
    # 检查环境
    check_git
    has_gh_cli=0
    check_gh_cli && has_gh_cli=1
    echo ""
    
    # 初始化仓库
    init_git_repo
    echo ""
    
    # 创建初始提交
    create_initial_commit
    echo ""
    
    # 创建GitHub仓库
    create_github_repo
    echo ""
    
    # 推送代码
    push_to_github
    echo ""
    
    # 配置GitHub功能
    if [ $has_gh_cli -eq 1 ]; then
        setup_github_pages
        echo ""
        
        setup_github_secrets
        echo ""
        
        read -p "是否创建首个Release? (y/n): " create_rel
        if [ "$create_rel" = "y" ]; then
            create_release
        fi
    else
        print_warning "跳过高级配置（需要GitHub CLI）"
    fi
    
    echo ""
    show_deployment_info
}

# 运行主函数
main
