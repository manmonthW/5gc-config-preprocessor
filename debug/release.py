#!/usr/bin/env python3
"""
发布工具模块
用于在软件发布时移除或禁用调试功能
"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Dict, Any

class ReleaseManager:
    """发布管理器 - 处理调试代码的分离"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.debug_dir = self.project_root / 'debug'
        self.backup_dir = self.project_root / '.debug_backup'
    
    def create_release_version(self, output_dir: Path = None) -> Path:
        """创建发布版本，移除调试相关代码"""
        if output_dir is None:
            output_dir = self.project_root.parent / f"{self.project_root.name}_release"
        
        output_dir = Path(output_dir)
        
        # 创建输出目录
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)
        
        # 复制项目文件，排除调试相关
        exclude_patterns = [
            'debug/',
            '__pycache__/',
            '*.pyc',
            '.git/',
            '.debug_backup/',
            'debug_report_*.md',
            'test_config.yaml',
            '*_debug.py',
            '*.log'
        ]
        
        self._copy_project_files(self.project_root, output_dir, exclude_patterns)
        
        # 清理API文件中的调试代码
        self._clean_api_files(output_dir)
        
        # 更新配置文件，禁用调试
        self._update_configs_for_release(output_dir)
        
        # 创建发布信息文件
        self._create_release_info(output_dir)
        
        print(f"Release version created at: {output_dir}")
        return output_dir
    
    def _copy_project_files(self, src_dir: Path, dst_dir: Path, exclude_patterns: List[str]):
        """复制项目文件，排除指定模式"""
        def should_exclude(path: str) -> bool:
            for pattern in exclude_patterns:
                if pattern.endswith('/'):
                    if f"{pattern}" in path or path.endswith(pattern[:-1]):
                        return True
                else:
                    if pattern in path or path.endswith(pattern):
                        return True
            return False
        
        for item in src_dir.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(src_dir)
                if not should_exclude(str(relative_path)):
                    dst_file = dst_dir / relative_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dst_file)
    
    def _clean_api_files(self, release_dir: Path):
        """清理API文件中的调试代码"""
        api_dir = release_dir / 'api'
        if not api_dir.exists():
            return
        
        for api_file in api_dir.glob('*.py'):
            self._remove_debug_code_from_file(api_file)
    
    def _remove_debug_code_from_file(self, file_path: Path):
        """从文件中移除调试相关代码"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除调试导入
        content = re.sub(
            r'# Import debug system.*?DEBUG_AVAILABLE = False.*?print\("Debug system not available".*?\)',
            '# Debug system disabled in release version\nDEBUG_AVAILABLE = False',
            content,
            flags=re.DOTALL
        )
        
        # 移除调试相关的代码块
        debug_patterns = [
            r'if DEBUG_AVAILABLE:.*?(?=\n\s*(?:def|class|\w+\s*=|\Z))',
            r'if DEBUG_AVAILABLE:.*?(?=\n\s*(?:except|finally|else))',
            r'if DEBUG_AVAILABLE:.*?log_api_request\([^)]*\)[^\n]*\n',
            r'if DEBUG_AVAILABLE:.*?log_api_response\([^)]*\)[^\n]*\n',
            r'if DEBUG_AVAILABLE:.*?api_logger\.[^(]*\([^)]*\)[^\n]*\n'
        ]
        
        for pattern in debug_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.MULTILINE)
        
        # 清理空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 移除调试相关的响应字段
        content = re.sub(r"'request_id': request_id,?\s*\n", '', content)
        content = re.sub(r"'debug_enabled': True,?\s*\n", '', content)
        content = re.sub(r"'debug_info': .*?,?\s*\n", '', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Cleaned debug code from: {file_path}")
    
    def _update_configs_for_release(self, release_dir: Path):
        """更新配置文件用于发布版本"""
        # 更新package.json
        package_json = release_dir / 'package.json'
        if package_json.exists():
            import json
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 移除开发依赖中的调试相关项
            if 'devDependencies' in data:
                data['devDependencies'].pop('vercel', None)
            
            # 更新脚本
            if 'scripts' in data:
                data['scripts'].pop('dev', None)
                if 'build' in data['scripts']:
                    data['scripts']['build'] = 'echo "Production build complete"'
            
            with open(package_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 创建生产环境配置
        env_file = release_dir / '.env'
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('DEBUG=false\n')
            f.write('LOG_LEVEL=ERROR\n')
            f.write('LOG_TO_FILE=false\n')
            f.write('LOG_TO_CONSOLE=false\n')
            f.write('DETAILED_ERRORS=false\n')
    
    def _create_release_info(self, release_dir: Path):
        """创建发布信息文件"""
        from datetime import datetime
        
        release_info = {
            'version': '1.0.0',
            'build_date': datetime.now().isoformat(),
            'type': 'production',
            'debug_enabled': False,
            'description': '5GC Config Preprocessor - Production Release'
        }
        
        with open(release_dir / 'release_info.json', 'w', encoding='utf-8') as f:
            import json
            json.dump(release_info, f, indent=2, ensure_ascii=False)
    
    def backup_debug_files(self):
        """备份调试文件"""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        shutil.copytree(self.debug_dir, self.backup_dir)
        print(f"Debug files backed up to: {self.backup_dir}")
    
    def restore_debug_files(self):
        """恢复调试文件"""
        if not self.backup_dir.exists():
            print("No backup found")
            return
        
        if self.debug_dir.exists():
            shutil.rmtree(self.debug_dir)
        
        shutil.copytree(self.backup_dir, self.debug_dir)
        print(f"Debug files restored from: {self.backup_dir}")
    
    def remove_debug_files(self):
        """移除调试文件（谨慎使用）"""
        if self.debug_dir.exists():
            # 先备份
            self.backup_debug_files()
            
            # 然后删除
            shutil.rmtree(self.debug_dir)
            print(f"Debug directory removed: {self.debug_dir}")
            print(f"Backup available at: {self.backup_dir}")

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Release Management Tool")
    parser.add_argument('--create-release', action='store_true', 
                       help='Create release version without debug code')
    parser.add_argument('--output-dir', type=str, 
                       help='Output directory for release version')
    parser.add_argument('--backup-debug', action='store_true', 
                       help='Backup debug files')
    parser.add_argument('--restore-debug', action='store_true', 
                       help='Restore debug files from backup')
    parser.add_argument('--remove-debug', action='store_true', 
                       help='Remove debug files (creates backup first)')
    
    args = parser.parse_args()
    
    # 确定项目根目录
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    
    manager = ReleaseManager(project_root)
    
    if args.create_release:
        output_dir = Path(args.output_dir) if args.output_dir else None
        manager.create_release_version(output_dir)
    elif args.backup_debug:
        manager.backup_debug_files()
    elif args.restore_debug:
        manager.restore_debug_files()
    elif args.remove_debug:
        manager.remove_debug_files()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()