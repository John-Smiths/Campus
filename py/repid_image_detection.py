from numpy import sum, mean, sqrt, ndarray
from cv2 import imread, resize, cvtColor, COLOR_BGR2GRAY, imshow, waitKey, destroyAllWindows, threshold, THRESH_BINARY, THRESH_BINARY, THRESH_OTSU

def ncc(image1, image2):
    # 计算每张图片的平均值
    mean1 = mean(image1)
    mean2 = mean(image2)

    # 计算协方差
    cov = sum((image1 - mean1) * (image2 - mean2))

    # 计算标准差
    sd1 = sqrt(sum((image1 - mean1) ** 2))
    sd2 = sqrt(sum((image2 - mean2) ** 2))

    # 防止分母为0
    if sd1 * sd2 == 0:
        return 0
    else:
        return cov / (sd1 * sd2)

def show_image(image, window_title):
    """
    显示给定的图像。

    参数:
        image (numpy.ndarray): 要显示的图像。
        window_title (str): 窗口标题。
    """
    imshow(window_title, image)
    waitKey(0)
    destroyAllWindows()

def image_detection(img_one, img_two):
    """
    比较两个已经转换为灰度图像的numpy数组是否表示同一个图像。
    参数:
        img_one (numpy.ndarray): 第一个输入图像，必须是已经被读取并转换为灰度的numpy数组。
        img_two (numpy.ndarray): 第二个输入图像，必须是已经被读取并转换为灰度的numpy数组。
    返回:
        float: 相似度。
    注意:可以使用此方法进行读取图像直接传入cv2.cvtColor(imread("image_path"), cv2.COLOR_BGR2GRAY),如果想进行图像整体检测则注释截取头部百分之10部分, cvtColor转化为灰度使检测更加快速
    """
    target_size = (min(img_one.shape[1], img_two.shape[1]), min(img_one.shape[0], img_two.shape[0]))
    img1_resized = resize(img_one, target_size)
    img2_resized = resize(img_two, target_size)

    # 使用图像的上10
    top_10_percent_height = int(target_size[0] * 0.1)

    img1_resized_top = img1_resized[:top_10_percent_height, :]
    img2_resized_top = img2_resized[:top_10_percent_height, :]

    top_10_percent_height = int(target_size[1] * 0.1)  # 注意这里应该是target_size[1]，因为它是高度
    bottom_10_percent_height = int(target_size[1] * 0.9)

    half_width = int(target_size[0] * 0.2)
    half_width_right = int(target_size[0] * 0.7)

    img1_resized_top_left = img1_resized_top[:top_10_percent_height, :half_width]
    img2_resized_top_left = img2_resized_top[:top_10_percent_height, :half_width]

    img1_resized_top_right = img1_resized_top[:top_10_percent_height, half_width_right:]
    img2_resized_top_right = img2_resized_top[:top_10_percent_height, half_width_right:]

    img1_resized_bottom = img1_resized[bottom_10_percent_height:, :]
    img2_resized_bottom = img2_resized[bottom_10_percent_height:, :]

    return (ncc(img1_resized_top_left, img2_resized_top_left) + ncc(img1_resized_top_right, img2_resized_top_right) + (ncc(img1_resized_bottom, img2_resized_bottom) / 2 )) / 3


if __name__ == "__main__":
    from time import time
    img_list = []
    img_one = cvtColor(imread("38.jpg"), COLOR_BGR2GRAY)

    for i in range(1, 40):
        img_list.append(cvtColor(imread(f"{i}.jpg"), COLOR_BGR2GRAY))

    start = time()

    # show_image(img_one, "0%")
    n = 0
    for i in img_list:
       similarity = image_detection(img_one, i)
       if similarity > 0.5 and similarity != 1.0:
           print(similarity, f"与{n+1}是极度相似的")
           # show_image(i, "1")
       else:
           print(similarity, n+1)
       n += 1

    print("共时:", time()-start)
