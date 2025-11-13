from flask import Flask, request, jsonify, send_from_directory
import requests
import json
import random
import os

app = Flask(__name__)

# 读取配置文件
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return []

# 保存配置文件
def save_config(config_data):
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# 检查配置是否已存在（并返回索引）
def find_config_index(config_data, new_config):
    for i, config in enumerate(config_data):
        if (config.get('openId') == new_config.get('openId') and 
            config.get('phone') == new_config.get('phone')):
            return i
    return -1

# 全局headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 9; SM-S9160 Build/PQ3A.190605.06171036; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/24.0)',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'Content-Type': 'application/json',
}

@app.route('/addUserConfig', methods=['POST'])
def add_user_config():
    """
    添加或更新用户配置接口
    """
    try:
        # 获取请求数据
        data = request.get_json()
        openId = data.get('openId')
        phone = data.get('phone')
        authorization = data.get('Authorization')
        
        # 检查必要参数
        if not openId or not phone or not authorization:
            return jsonify({'error': '缺少必要的参数: openId, phone, Authorization'}), 400
        
        # 构造请求头
        headers_with_auth = headers.copy()
        headers_with_auth['Authorization'] = "Bearer " + authorization

        # 构造请求数据
        json_data = {
            'openId': openId,
            'phone': phone,
            'couponStatus': 'unused'
        }

        # 发送验证请求
        response = requests.post(
            'https://recharge3.bac365.com/camel_wechat_mini_oil_server/refueling/getUserCouponList',
            headers=headers_with_auth,
            json=json_data,
        ).json()
        
        # 检查响应是否成功
        if response.get('code') == 'success':
            # 加载现有配置
            config_data = load_config()
            
            # 创建新配置项
            new_config = {
                'openId': openId,
                'phone': phone,
                'Authorization': authorization
            }
            
            # 检查是否已存在
            index = find_config_index(config_data, new_config)
            
            if index >= 0:
                # 如果存在，则更新Authorization
                config_data[index]['Authorization'] = authorization
                action = 'updated'
                message = '用户配置更新成功'
            else:
                # 如果不存在，则添加新配置
                config_data.append(new_config)
                action = 'added'
                message = '用户配置添加成功'
            
            # 保存配置文件
            if save_config(config_data):
                return jsonify({
                    'message': message,
                    'action': action,
                    'code': 'success',
                    'data': response
                })
            else:
                return jsonify({'error': '配置保存失败'}), 500
        else:
            return jsonify({
                'message': '认证信息验证失败',
                'code': 'auth_failed',
                'data': response
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/userECardQueryApi', methods=['POST'])
def user_ecard_query_api():
    """
    查询加油卡状态接口
    """
    try:
        # 获取请求数据
        data = request.get_json()
        cardNo = data.get('cardNo')
        cardCode = data.get('cardCode')
        
        # 从配置文件中随机获取token、openId和phone
        config = get_random_config()
        if not config:
            return jsonify({'error': '无法从配置文件中获取认证信息'}), 500
            
        token = config['token']
        openId = config['openId']
        phone = config['phone']
        
        # 构造请求头
        headers_with_auth = headers.copy()
        headers_with_auth['Authorization'] = "Bearer " + token 
        
        # 构造请求数据
        json_data = {
            'openId': openId,
            'cardNo': cardNo,
            'cardCode': cardCode,
            'phone': phone,
        }

        # 发送请求
        response = requests.post(
            'https://recharge3.bac365.com/camel_wechat_mini_oil_server/eCard/userECardQueryApi',
            headers=headers_with_auth,
            json=json_data,
        ).json()
        
        # 重新构建返回结果，根据status字段判断卡片状态
        if 'cardRes' in response and 'status' in response['cardRes']:
            status = response['cardRes']['status']
            if status == '1':
                response['cardStatus'] = '已使用'
                response['cardStatusDesc'] = '该加油卡已被使用'
            elif status == '0':
                response['cardStatus'] = '未使用'
                response['cardStatusDesc'] = '该加油卡未被使用'
            else:
                response['cardStatus'] = '未知状态'
                response['cardStatusDesc'] = f'卡片状态未知: {status}'
        else:
            response['cardStatus'] = '无状态信息'
            response['cardStatusDesc'] = '无法获取卡片状态信息'
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/eCardRecharge', methods=['POST'])
def ecard_recharge():
    """
    加油卡充值接口
    """
    try:
        # 获取请求数据
        data = request.get_json()
        eCardCode = data.get('eCardCode')
        
        # 从配置文件中随机获取token、openId和phone
        config = get_random_config()
        if not config:
            return jsonify({'error': '无法从配置文件中获取认证信息'}), 500
            
        token = config['token']
        openId = config['openId']
        phone = config['phone']
        
        # 构造请求头
        headers_with_auth = headers.copy()
        headers_with_auth['Authorization'] = "Bearer " + token

        # 构造请求数据
        json_data = {
            'eCardCode': eCardCode,
            'openId': openId,
            'phone': phone,
        }

        # 发送请求
        response = requests.post(
            'https://recharge3.bac365.com/camel_wechat_mini_oil_server/eCardMall/eCardRecharge',
            headers=headers_with_auth,
            json=json_data,
        ).json()
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 健康检查接口
@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    return jsonify({'status': 'healthy', 'message': '服务正常运行中'})

# 提供静态文件
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# 随机获取配置
def get_random_config():
    config = load_config()
    if config and len(config) > 0:
        # 随机选择一个配置
        selected_config = random.choice(config)
        return {
            'token': selected_config.get('Authorization', ''),
            'openId': selected_config.get('openId', ''),
            'phone': selected_config.get('phone', '')
        }
    return None

# Vercel 需要的入口点
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)