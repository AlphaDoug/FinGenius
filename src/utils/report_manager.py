"""
增强的报告管理器
专门处理FinGenius的分析报告类型：
1. 主分析报告JSON - 包含专家总结、股票详情、投票结果
2. 原始数据JSON - API获取的股票基础信息数据
3. 按时间戳创建文件夹统一管理
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.logger import logger
from src.schema.expert_summary import AnalysisReport


class EnhancedReportManager:
    """增强的报告管理器"""
    
    def __init__(self, base_dir: str = "analysis_reports"):
        self.base_dir = Path(base_dir)
        self.ensure_directories()
        
        # 保留期限（天）
        self.retention_days = 30
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_timestamped_folder(self, stock_code: str, timestamp: str = None) -> Path:
        """创建基于时间戳的文件夹"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        folder_name = f"{stock_code}_{timestamp}"
        folder_path = self.base_dir / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        return folder_path
    
    def save_analysis_report(
        self, 
        stock_code: str, 
        analysis_report: AnalysisReport,
        raw_stock_data: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """
        保存完整的分析报告
        
        Args:
            stock_code: 股票代码
            analysis_report: 分析报告对象
            raw_stock_data: 原始股票数据
            
        Returns:
            Dict[str, str]: 保存的文件路径信息
        """
        try:
            # 创建时间戳文件夹
            folder_path = self.create_timestamped_folder(stock_code, analysis_report.timestamp)
            
            # 保存主分析报告
            main_report_path = folder_path / "analysis_report.json"
            with open(main_report_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_report.model_dump(), f, ensure_ascii=False, indent=2)
            
            # 保存原始股票数据（如果提供）
            raw_data_path = None
            if raw_stock_data:
                raw_data_path = folder_path / "raw_stock_data.json"
                with open(raw_data_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_stock_data, f, ensure_ascii=False, indent=2)
            
            # 保存元数据
            metadata = {
                "stock_code": stock_code,
                "timestamp": analysis_report.timestamp,
                "analysis_duration": analysis_report.analysis_duration,
                "expert_count": len(analysis_report.expert_summaries),
                "total_votes": analysis_report.voting_results.total_votes,
                "final_decision": analysis_report.voting_results.final_decision,
                "created_at": datetime.now().isoformat(),
                "folder_path": str(folder_path)
            }
            
            metadata_path = folder_path / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析报告保存成功: {folder_path}")
            
            return {
                "folder_path": str(folder_path),
                "main_report": str(main_report_path),
                "raw_data": str(raw_data_path) if raw_data_path else None,
                "metadata": str(metadata_path)
            }
            
        except Exception as e:
            logger.error(f"保存分析报告失败 {stock_code}: {str(e)}")
            raise
    
    def load_analysis_report(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """加载分析报告"""
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return None
            
            # 读取主报告
            main_report_path = folder / "analysis_report.json"
            if not main_report_path.exists():
                return None
            
            with open(main_report_path, 'r', encoding='utf-8') as f:
                main_report = json.load(f)
            
            # 读取原始数据（可选）
            raw_data = None
            raw_data_path = folder / "raw_stock_data.json"
            if raw_data_path.exists():
                with open(raw_data_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            
            # 读取元数据
            metadata = {}
            metadata_path = folder / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            return {
                "main_report": main_report,
                "raw_data": raw_data,
                "metadata": metadata,
                "folder_path": str(folder)
            }
            
        except Exception as e:
            logger.error(f"加载分析报告失败 {folder_path}: {str(e)}")
            return None
    
    def list_analysis_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出分析报告"""
        reports = []
        
        try:
            # 获取所有文件夹，按时间排序
            folders = [f for f in self.base_dir.iterdir() if f.is_dir()]
            folders.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for folder in folders[:limit]:
                metadata_path = folder / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    reports.append({
                        "folder_name": folder.name,
                        "folder_path": str(folder),
                        "stock_code": metadata.get("stock_code"),
                        "timestamp": metadata.get("timestamp"),
                        "final_decision": metadata.get("final_decision"),
                        "created_at": metadata.get("created_at"),
                        "analysis_duration": metadata.get("analysis_duration")
                    })
            
        except Exception as e:
            logger.error(f"列出分析报告失败: {str(e)}")
        
        return reports
    
    def cleanup_old_reports(self):
        """清理过期报告"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0
            
            for folder in self.base_dir.iterdir():
                if folder.is_dir():
                    folder_time = datetime.fromtimestamp(folder.stat().st_mtime)
                    if folder_time < cutoff_date:
                        import shutil
                        shutil.rmtree(folder)
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个过期报告文件夹")
                
        except Exception as e:
            logger.error(f"清理过期报告失败: {str(e)}")

    # 保留旧版本兼容性方法
    def save_debate_report(self, stock_code: str, debate_data: Dict, 
                          metadata: Optional[Dict] = None) -> bool:
        """保存辩论对话JSON（兼容性方法）"""
        logger.warning("save_debate_report 已废弃，请使用 save_analysis_report")
        return True
    
    def save_vote_report(self, stock_code: str, vote_data: Dict, 
                        metadata: Optional[Dict] = None) -> bool:
        """保存投票结果JSON（兼容性方法）"""
        logger.warning("save_vote_report 已废弃，请使用 save_analysis_report")
        return True

    def save_analysis_data(self, stock_code: str, analysis_data: Dict,
                           metadata: Optional[Dict] = None) -> bool:
        """保存完整分析数据JSON（兼容性方法）"""
        logger.warning("save_analysis_data 已废弃，请使用 save_analysis_report")

# 全局报告管理器实例
report_manager = EnhancedReportManager()