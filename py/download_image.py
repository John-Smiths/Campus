import asyncio
import aiohttp
import base64
import re
from pathlib import Path
from PIL import Image
from io import BytesIO
from urllib.parse import urlparse

class ImageDownloader:
    def __init__(self, save_dir='../db'):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True, parents=True)
    
    async def download(self, url: str, name: str) -> bool:
        """
        异步下载单张图片并转换为JPG格式
        自动检测URL返回的内容类型（base64或二进制文件）
        
        Args:
            url: 图片URL地址
            name: 保存的文件名（不含扩展名）
        
        Returns:
            bool: 下载成功返回True，失败返回False
        """
        try:
            print(f"开始下载: {name} <- {url}")
            
            # 下载URL内容
            image_data = await self._fetch_url_content(url)
            
            if image_data:
                # 转换并保存为JPG
                await self._save_as_jpg(image_data, name)
                print(f"✓ 成功保存: {name}.jpg")
                return True
            else:
                print(f"✗ 下载失败: {name}")
                return False
                
        except Exception as e:
            print(f"✗ 错误 {name}: {str(e)}")
            return False
    
    async def _fetch_url_content(self, url: str) -> bytes:
        """
        从URL获取内容，自动检测是base64还是二进制文件
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                # 获取响应内容
                content = await response.read()
                content_type = response.headers.get('Content-Type', '').lower()
                
                # 判断内容类型
                print(f"  Content-Type: {content_type if content_type else 'unknown'}")
                
                # 如果是图片类型，直接返回二进制数据
                if content_type.startswith('image/'):
                    print(f"  检测到: 二进制图片文件")
                    return content
                
                # 尝试作为文本解析（可能是base64）
                try:
                    text_content = content.decode('utf-8')
                    
                    # 检测是否为base64格式
                    if self._is_base64_string(text_content):
                        print(f"  检测到: Base64编码文本")
                        return self._decode_base64(text_content)
                    
                except UnicodeDecodeError:
                    pass
                
                # 默认当作二进制图片文件处理
                print(f"  检测到: 二进制文件")
                return content
    
    def _is_base64_string(self, text: str) -> bool:
        """检测文本是否为base64格式"""
        text = text.strip()
        
        # 检测data URI格式
        if text.startswith('data:image'):
            return True
        
        # 检测纯base64字符串
        # base64字符只包含: A-Z, a-z, 0-9, +, /, =
        if re.match(r'^[A-Za-z0-9+/]+=*$', text):
            # 尝试解码验证
            try:
                decoded = base64.b64decode(text)
                # 检查是否为有效图片（简单检查文件头）
                return self._is_image_data(decoded)
            except:
                pass
        
        return False
    
    def _is_image_data(self, data: bytes) -> bool:
        """检查二进制数据是否为图片"""
        # 检查常见图片格式的文件头
        image_signatures = [
            b'\xFF\xD8\xFF',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF87a',  # GIF
            b'GIF89a',  # GIF
            b'RIFF',  # WebP (需要进一步检查)
            b'BM',  # BMP
        ]
        return any(data.startswith(sig) for sig in image_signatures)
    
    def _decode_base64(self, data: str) -> bytes:
        """解码base64图片数据"""
        data = data.strip()
        
        # 处理data URI格式: data:image/png;base64,iVBORw0KG...
        if data.startswith('data:'):
            match = re.match(r'data:image/[^;]+;base64,(.+)', data)
            if match:
                data = match.group(1)
        
        # 解码base64
        return base64.b64decode(data)
    
    async def _save_as_jpg(self, image_data: bytes, name: str):
        """将图片数据转换为JPG格式并保存"""
        # 使用asyncio在线程池中执行IO密集型操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._convert_and_save, image_data, name)
    
    def _convert_and_save(self, image_data: bytes, name: str):
        """转换图片格式并保存（同步操作）"""
        # 打开图片
        img = Image.open(BytesIO(image_data))
        
        print(f"  原始格式: {img.format}, 模式: {img.mode}, 尺寸: {img.size}")
        
        # 如果是RGBA模式，转换为RGB（JPG不支持透明度）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 保存为JPG
        save_path = self.save_dir / f"{name}.jpg"
        img.save(save_path, 'JPEG', quality=95, optimize=True)


# 提供便捷的模块级函数供外部调用
_default_downloader = None

def get_downloader(save_dir='../db'):
    """获取默认下载器实例"""
    global _default_downloader
    if _default_downloader is None:
        _default_downloader = ImageDownloader(save_dir)
    return _default_downloader

async def download(url: str, name: str, save_dir='../db') -> bool:
    """
    便捷函数：下载单张图片
    
    Args:
        url: 图片URL地址
        name: 保存的文件名（不含扩展名）
        save_dir: 保存目录，默认为'../db'
    
    Returns:
        bool: 下载成功返回True，失败返回False
    
    使用示例:
        import asyncio
        from image_downloader import download
        
        asyncio.run(download('https://example.com/image.png', 'my_image'))
    """
    downloader = ImageDownloader(save_dir)
    return await downloader.download(url, name)


# 命令行测试
if __name__ == '__main__':
    async def test():
        downloader = ImageDownloader(save_dir='../db')
        
        # 测试普通图片URL
        test_urls = [
            ('https://multimedia.nt.qq.com.cn/download?appid=1407&fileid=EhRJz6MdH9WV-KZ5868AsipH1OQAexid8gkg_woonf2xoLWFkAMyBHByb2RQgL2jAVoQHQwFKI0TPrLBTAGSLKnRgHoC42GCAQJneg&rkey=CAMSOLgthq-6lGU_wNjMJK9fXGAQaq5wHa1xIMfd3FYzz2mqVzja4kV15fKLRsfBL8s3zH2g9PCOx3-o&spec=0', 'test_binary'),
            # 如果你有base64返回的URL，可以在这里测试
        ]
        
        for url, name in test_urls:
            await downloader.download(url, name)
            print('-' * 50)
    
    asyncio.run(test())
