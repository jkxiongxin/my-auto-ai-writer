"""测试前后端字数分级一致性."""

import re
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_word_count_consistency():
    """测试前后端字数分级一致性."""
    try:
        logger.info("开始测试前后端字数分级一致性...")
        
        # 读取前端HTML文件
        with open('frontend/index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 读取前端JavaScript文件
        with open('frontend/script.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # 读取后端概念扩展器文件
        with open('src/core/concept_expander.py', 'r', encoding='utf-8') as f:
            backend_content = f.read()
        
        # 提取前端HTML中的字数选项
        html_options = re.findall(r'<option value="(\d+)"[^>]*>[^<]+</option>', html_content)
        html_word_counts = [int(x) for x in html_options]
        
        # 提取前端JavaScript中的验证范围
        js_validation = re.search(r'data\.target_words < (\d+) \|\| data\.target_words > (\d+)', js_content)
        if js_validation:
            js_min = int(js_validation.group(1))
            js_max = int(js_validation.group(2))
        else:
            logger.error("无法找到JavaScript验证范围")
            return False
        
        # 提取后端验证范围
        backend_validation = re.search(r'(\d+) <= target_words <= (\d+)', backend_content)
        if backend_validation:
            backend_min = int(backend_validation.group(1))
            backend_max = int(backend_validation.group(2))
        else:
            logger.error("无法找到后端验证范围")
            return False
        
        # 验证一致性
        logger.info(f"前端HTML字数选项: {sorted(html_word_counts)}")
        logger.info(f"前端JavaScript验证范围: {js_min} - {js_max}")
        logger.info(f"后端验证范围: {backend_min} - {backend_max}")
        
        # 检查JavaScript和后端范围是否一致
        if js_min != backend_min or js_max != backend_max:
            logger.error(f"❌ JavaScript和后端验证范围不一致!")
            logger.error(f"JavaScript: {js_min} - {js_max}")
            logger.error(f"后端: {backend_min} - {backend_max}")
            return False
        
        # 检查HTML选项是否在有效范围内
        min_option = min(html_word_counts)
        max_option = max(html_word_counts)
        
        if min_option < backend_min or max_option > backend_max:
            logger.error(f"❌ HTML选项超出后端验证范围!")
            logger.error(f"HTML范围: {min_option} - {max_option}")
            logger.error(f"后端范围: {backend_min} - {backend_max}")
            return False
        
        # 检查是否包含最小值选项
        if backend_min not in html_word_counts:
            logger.warning(f"⚠️ HTML选项中缺少最小值 {backend_min}")
        
        # 检查是否包含最大值选项
        if backend_max not in html_word_counts:
            logger.warning(f"⚠️ HTML选项中缺少最大值 {backend_max}")
        
        logger.info("✅ 前后端字数分级一致性检查通过!")
        logger.info(f"支持范围: {backend_min:,} - {backend_max:,} 字")
        logger.info(f"可选档位: {len(html_word_counts)} 个")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 字数分级一致性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数."""
    print("🧪 前后端字数分级一致性测试")
    print("=" * 50)
    
    # 测试字数分级一致性
    consistency_test = test_word_count_consistency()
    
    # 结果总结
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"字数分级一致性: {'✅ 通过' if consistency_test else '❌ 失败'}")
    
    if consistency_test:
        print("\n🎉 前后端字数分级已统一！")
        print("✅ 用户现在可以看到完整的字数选项范围")
        print("✅ 前端验证与后端验证保持一致")
    else:
        print("\n⚠️ 字数分级存在不一致问题，需要进一步调整")

if __name__ == "__main__":
    main()