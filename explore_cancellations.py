# 探索 Personal Line > Cancellations 文件夹
import smartsheet
import os

print("正在连接到 Smartsheet...")

# 使用环境变量中的 token
smart = smartsheet.Smartsheet()
smart.errors_as_exceptions(True)

# Cancellations 文件夹 ID (从之前的结果中获取)
cancellations_folder_id = 6500165851867012

def get_folder_contents(folder_id, folder_name):
    """获取文件夹中的所有内容"""
    try:
        print(f'\n📁 正在查看文件夹: {folder_name}')
        print(f'文件夹ID: {folder_id}')
        print('=' * 60)
        
        # 使用正确的 API 方法获取文件夹内容
        folder = smart.Folders.get_folder(folder_id)
        
        sheets_found = []
        subfolders_found = []
        
        # 检查文件夹中的工作表
        if hasattr(folder, 'sheets') and folder.sheets:
            sheets_found = folder.sheets
            print(f'📊 工作表 ({len(sheets_found)} 个):')
            print('-' * 40)
            for i, sheet in enumerate(sheets_found, 1):
                print(f'{i}. 名称: {sheet.name}')
                print(f'   ID: {sheet.id}')
                if hasattr(sheet, 'modified_at') and sheet.modified_at:
                    print(f'   修改时间: {sheet.modified_at}')
                if hasattr(sheet, 'created_at') and sheet.created_at:
                    print(f'   创建时间: {sheet.created_at}')
                print()
        else:
            print('📊 没有找到工作表')
        
        # 检查子文件夹
        if hasattr(folder, 'folders') and folder.folders:
            subfolders_found = folder.folders
            print(f'📁 子文件夹 ({len(subfolders_found)} 个):')
            print('-' * 40)
            for i, subfolder in enumerate(subfolders_found, 1):
                print(f'{i}. 名称: {subfolder.name}')
                print(f'   ID: {subfolder.id}')
                print()
        else:
            print('📁 没有找到子文件夹')
        
        # 检查报告
        if hasattr(folder, 'reports') and folder.reports:
            print(f'📈 报告 ({len(folder.reports)} 个):')
            print('-' * 40)
            for i, report in enumerate(folder.reports, 1):
                print(f'{i}. 名称: {report.name}')
                print(f'   ID: {report.id}')
                print()
        
        # 检查仪表板
        if hasattr(folder, 'dashboards') and folder.dashboards:
            print(f'📋 仪表板 ({len(folder.dashboards)} 个):')
            print('-' * 40)
            for i, dashboard in enumerate(folder.dashboards, 1):
                print(f'{i}. 名称: {dashboard.name}')
                print(f'   ID: {dashboard.id}')
                print()
        
        return sheets_found, subfolders_found
        
    except Exception as e:
        print(f'获取文件夹内容时出错: {e}')
        return [], []

try:
    print(f'\n=== Personal Line > Cancellations 文件夹内容 ===')
    
    # 获取 Cancellations 文件夹的内容
    sheets, subfolders = get_folder_contents(cancellations_folder_id, "Cancellations")
    
    # 如果有子文件夹，也显示它们的内容
    if subfolders:
        print(f'\n{"="*60}')
        print('子文件夹详细内容:')
        for subfolder in subfolders:
            get_folder_contents(subfolder.id, f"Cancellations > {subfolder.name}")
    
    # 提供操作建议
    if sheets:
        print(f'\n{"="*60}')
        print('📋 可用操作:')
        print('1. 查看特定工作表的详细信息')
        print('2. 读取工作表数据')
        print('3. 更新工作表内容')
        print('4. 导出工作表数据')
        print('\n请告诉我您想对哪个工作表进行什么操作！')

except Exception as e:
    print(f'错误: {e}')
    print('请确保您有访问该文件夹的权限')
