import streamlit as st
from utils.chat_utils import get_response_from_bot, get_response_from_bot_group, display_chat, display_group_chat
from custom_pages.utils.dialogs import edit_bot, add_new_bot
from datetime import datetime, date
import random
from config import EMOJI_OPTIONS, ENGINE_OPTIONS, ENGINE_NAMES, LOGGER
import importlib
import os

def display_active_bots(bot_manager, prompt, show_bots):
    num_bots = len(show_bots)
    num_cols = min(2, num_bots)
    cols = st.columns(num_cols)

    for i, bot in enumerate(show_bots):
        if not bot['enable']:
            continue
        col = cols[i % num_cols]
        with col:
            button_box, title_box = st.columns([1, 10], gap="small")
            
            # 获取当前bot的历史记录
            current_history = bot_manager.get_current_history_by_bot(bot)
            
            if prompt:
                response_content = get_response_from_bot(prompt, bot, bot_manager.get_current_history_by_bot(bot))
                bot_manager.add_message_to_history(bot['id'], {"role": "user", "content": prompt})
                bot_manager.add_message_to_history(bot['id'], {"role": "assistant", "content": response_content})
                bot_manager.fix_history_names(bot_manager.current_history_version_idx)
                current_history = bot_manager.get_current_history_by_bot(bot)

            if current_history:
                display_chat(bot, current_history)

                with button_box:
                    show_bot_avatar(bot)
                with title_box:
                    show_bot_title(bot)

def display_inactive_bots(bot_manager, show_bots):
    show_bots = show_bots + [{'id': 'new_bot', 'avatar': '⚡', 'name': '新增一个Bot', 'engine': f'支持{len(ENGINE_OPTIONS)}种API引擎'}]

    num_bots = len(show_bots)
    
    if st.session_state.page == 'main_page':
        num_cols = min(2, num_bots)
        title_box_width = 10
    else:
        num_cols = 4
        title_box_width = 4

    cols = st.columns(num_cols, gap="large")

    for i, bot in enumerate(show_bots):
        col = cols[i % num_cols]
        with col:
            button_box, title_box = st.columns([1, title_box_width], gap="small")
            
            with button_box:
                if bot['id'] == 'new_bot':
                    if st.button(bot.get('avatar', '') or '🤖', key=f"__edit_enabled_bot_{bot['id']}"):
                        st.session_state.avatar = random.choice(EMOJI_OPTIONS)
                        add_new_bot()
                else:
                    show_bot_avatar(bot)
                    
            with title_box:
                show_bot_title(bot)
                if bot['id'] == 'new_bot':
                    if st.button("创建Bot好友", key=f"create_new_bot_{bot['id']}", type="primary"):
                        st.session_state.avatar = random.choice(EMOJI_OPTIONS)
                        add_new_bot()
                else:
                    show_toggle_bot_enable(bot)
                    if st.session_state.page == 'main_page':
                        all_histories = bot_manager.get_all_histories(bot)
                        non_empty_histories = [h for h in all_histories[:-1] if h['history']]

                        if non_empty_histories:
                            num_topics = len(non_empty_histories)
                            with st.expander(f"查看 {num_topics} 个历史话题"):
                                for i, history in enumerate(reversed(non_empty_histories)):
                                    try:
                                        timestamp = datetime.fromisoformat(history['timestamp'])
                                    except ValueError:
                                        timestamp = datetime.strptime(history['timestamp'], "%Y-%m-%d %H:%M:%S")
                                    
                                    today = date.today()
                                    if timestamp.date() == today:
                                        formatted_time = f"今天 {timestamp.strftime('%H:%M')}"
                                    else:
                                        formatted_time = timestamp.strftime("%Y年%m月%d日 %H:%M")
                                    
                                    st.markdown(f"**{history['name']}** - {formatted_time}")
                                    display_chat(bot, history['history'])
            
            if i < len(show_bots) - num_cols:
                st.markdown("---")

def display_group_chat_area(bot_manager, show_bots, histories):
    col1, col2 = st.columns([1,1], gap="small")
    with col1:
        if histories:
            participating_bots = bot_manager.get_participating_bots_in_current_group_history()
            display_group_chat(participating_bots, histories)
            
            col_left, col_right = st.columns([1,1], gap="small")

            # 添加删除最近回复的按钮
            with col_left:
                if histories:
                    if st.button(f"删除上一条", key="delete_last_reply", use_container_width=True, help="删除聊天记录中的最后一条消息"):
                        bot_manager.remove_last_group_message()
                        st.rerun()
            
            # 添加删除最近几条Bot回复的按钮
            with col_right:
                if histories:
                    if st.button(f"删除Bot近期回复", key="delete_recently_bot_reply", use_container_width=True, help="删除最后几条由Bot发布的消息"):
                        bot_manager.remove_recently_bot_group_message()
                        st.rerun()
    with col2:
        if st.session_state.tool_manager.tools:
            # 添加工具箱
            st.markdown("### 工具箱")
            tool_cols = st.columns(4)
            
            # 对工具进行排序
            sorted_tools = sorted(st.session_state.tool_manager.tools, key=lambda x: x["name"])
            
            for i, tool in enumerate(sorted_tools):  
                with tool_cols[i % 4]:
                    if st.button(tool["name"], use_container_width=True, key=f"use_tool_{i}", help=f"{tool['description'][0:100]}\n\n***【点击按钮可调用】***".strip()):
                        use_tool(tool['id'], True)

        enabled_bots = [bot for bot in show_bots if bot['enable']]
        disabled_bots = [bot for bot in show_bots if not bot['enable']]

        st.markdown("### 幕僚")
        
        # 幕僚设置区域，使用三个列排列开关
        col1, col2, col3 = st.columns(3)
        
        # 幕僚自动发言开关
        with col1:
            auto_speak = st.toggle("幕僚自动发言", value=bot_manager.get_auto_speak(), help="优先由预设大模型挑选要发言的幕僚，如果规划失败，则按顺序让所有幕僚依次发言")
            if auto_speak != bot_manager.get_auto_speak():
                bot_manager.set_auto_speak(auto_speak)
                st.rerun()
        
        # 机器人同时回答开关
        with col2:
            all_bots_speak = st.toggle("机器人同时回答", value=bot_manager.get_all_bots_speak(), key="all_bots_speak", 
                                    help="开启后，所有机器人将同时回答问题。关闭则选择最合适的机器人回答。")
            if all_bots_speak != bot_manager.get_all_bots_speak():
                bot_manager.set_all_bots_speak(all_bots_speak)
                st.rerun()
                
        # 添加"所有机器人加入观众"开关
        with col3:
            # 从bot_manager获取设置状态
            all_bots_as_audience = st.toggle("所有机器人加入观众", 
                                           value=bot_manager.get_all_bots_as_audience(),
                                           key="all_bots_as_audience",
                                           help="开启后，所有机器人将被显示在观众区域，方便单独点击调用")
            
            # 如果状态改变，更新bot_manager中的设置
            if all_bots_as_audience != bot_manager.get_all_bots_as_audience():
                bot_manager.set_all_bots_as_audience(all_bots_as_audience)
                st.rerun()

        if enabled_bots:
            num_bots = len(enabled_bots)
            num_cols = min(2, num_bots)

            cols = st.columns(num_cols)

            for i, bot in enumerate(enabled_bots):
                col = cols[i % num_cols]
                with col:
                    chat_config = bot_manager.get_chat_config()
                    group_user_prompt = chat_config.get('group_user_prompt')
                    if st.button(f"{bot.get('avatar', '🤖')} {bot['name']}\n\n{ENGINE_NAMES.get(bot['engine'],bot['engine'])} {bot.get('model','')}", key=f"group_bot_{bot['id']}", help=f"{bot.get('system_prompt','')[0:100]}\n\n***【点击按钮可手动发言】***".strip(), use_container_width=True):
                        response_content = get_response_from_bot_group(group_user_prompt, bot, histories)
                        bot_manager.add_message_to_group_history("assistant", response_content, bot=bot)
                        bot_manager.save_data_to_file()
                        st.rerun()
        
        st.markdown("### 观众")
        st.markdown("未启用的Bot作为观众，点击按钮可以手动发言")
        
        # 添加新Bot按钮
        if st.button("➕ 添加新Bot", key="add_new_audience_bot", use_container_width=False):
            st.session_state.avatar = random.choice(EMOJI_OPTIONS)
            add_new_bot()
        
        # 根据"所有机器人加入观众"开关状态决定显示哪些机器人
        audience_bots = []
        if bot_manager.get_all_bots_as_audience():
            # 如果开关开启，显示所有机器人（包括已启用的）
            audience_bots = show_bots
        else:
            # 如果关闭，只显示未启用的机器人
            audience_bots = disabled_bots
        
        # 添加"新增Bot"选项到观众列表
        # 不使用audience_bots_with_new，避免嵌套列问题
            
        if audience_bots:
            num_bots = len(audience_bots)
            num_cols = min(4, num_bots)  # 使用4列显示观众机器人

            cols = st.columns(num_cols)

            for i, bot in enumerate(audience_bots):
                col = cols[i % num_cols]
                with col:
                    # 只显示常规机器人按钮
                    chat_config = bot_manager.get_chat_config()
                    group_user_prompt = chat_config.get('group_user_prompt')
                    # 使用不同的key前缀避免按钮ID冲突
                    button_key = f"audience_bot_{bot['id']}" if bot_manager.get_all_bots_as_audience() else f"group_bot_{bot['id']}"
                    if st.button(f"{bot.get('avatar', '🤖')} {bot['name']}\n\n{ENGINE_NAMES.get(bot['engine'],bot['engine'])} {bot.get('model','')}", key=button_key, help=f"{bot.get('system_prompt','')[0:100]}\n\n***【点击按钮可手动发言】***".strip(), use_container_width=True):
                        response_content = get_response_from_bot_group(group_user_prompt, bot, histories)
                        bot_manager.add_message_to_group_history("assistant", response_content, bot=bot)
                        bot_manager.save_data_to_file()
                        st.rerun()
        elif not bot_manager.get_all_bots_as_audience():
            # 当没有未启用的Bot且"所有机器人加入观众"未开启时，显示相应提示
            st.info("当前没有未启用的Bot作为观众。您可以在Bot管理中禁用一些Bot，它们将在这里显示为观众。")
            
            # 显示未参与当前群聊的机器人作为观众
            if histories:
                active_bots = bot_manager.get_participating_bots_in_current_group_history()
                inactive_bots = [bot for bot in show_bots if bot['enable'] and bot['id'] not in [active_bot['id'] for active_bot in active_bots]]
                
                if inactive_bots:
                    st.markdown("##### 未参与当前对话的Bot：")
                    for bot in inactive_bots:
                        st.markdown(f"🔘 {bot.get('avatar', '🤖')} {bot['name']}")

# 辅助函数保持不变
def show_bot_avatar(bot):
    bot_manager = st.session_state.bot_manager
    if st.button(bot.get('avatar', '') or '🤖', key=f"__avatar_edit_bot_{bot['id']}", help=f"{bot.get('system_prompt','')[0:100]}\n\n***【点击头像可编辑】***".strip()):
        edit_bot(bot)

def show_bot_title(bot):
   st.markdown(f"<h3 style='padding:0;'>{bot['name']}</h3> {ENGINE_NAMES.get(bot['engine'],bot['engine'])} {bot.get('model', '')}", unsafe_allow_html=True)

def show_toggle_bot_enable(bot):
    def make_update_bot_enable(bot_id):
        def update_bot_enable():
            bot = next((b for b in st.session_state.bots if b['id'] == bot_id), None)
            if bot:
                bot['enable'] = not bot['enable']
                st.session_state.bot_manager.update_bot(bot)
        return update_bot_enable

    st.toggle("启用 / 禁用", value=bot['enable'], key=f"toggle_{bot['id']}", on_change=make_update_bot_enable(bot['id']))

def use_tool_once(tool_folder):
    bot_manager = st.session_state.bot_manager
    tool_info = st.session_state.tool_manager.tool_map.get(tool_folder)

    if not tool_info:
        st.error(f"找不到工具: {tool_folder}")
        return

    # try:
    # 动态导入工具模块
    tool_module = importlib.import_module(f"tools.{tool_folder}.{tool_info['main_file'][:-3]}")
    
    # 获取最后一条消息内容
    group_history = bot_manager.get_current_group_history()
    last_message = group_history[-1]['content'] if group_history else ""
    # 调用工具
    results = tool_module.run(tool_info.get('config',{}), last_message, st.session_state.chat_config.get('group_user_prompt', ''), group_history)
    
    if type(results) == list:
        for result in results:
            if result:
                bot_manager.add_message_to_group_history("assistant", result, tool=tool_info)
    else:
        if results:
            bot_manager.add_message_to_group_history("assistant", results, tool=tool_info)

    # except Exception as e:
    #     st.error(f"执行工具时出错: {e}")

def use_tool(tool_folder, show_planning=False):
    bot_manager = st.session_state.bot_manager
    tool_manager = st.session_state.tool_manager
    tool_info = st.session_state.tool_manager.tool_map.get(tool_folder)

    if not tool_info:
        st.error(f"找不到工具: {tool_folder}")
        return

    try:
        # 动态导入工具模块
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        tool_path = os.path.join(base_dir, 'tools', tool_folder, tool_info['main_file'])
        LOGGER.info(f"工具文件路径: {tool_path}")
        
        if not os.path.exists(tool_path):
            st.error(f"工具文件不存在: {tool_path}")
            return
        
        # 使用绝对导入路径
        module_name = f"tools.{tool_folder}.{tool_info['main_file'][:-3]}"
        LOGGER.info(f"正在导入工具模块: {module_name}")
        tool_module = importlib.import_module(module_name)
        
        # 获取最后一条消息内容
        group_history = bot_manager.get_current_group_history()
        last_message = group_history[-1]['content'] if group_history else ""
        # 调用工具
        group_user_prompt = st.session_state.chat_config.get("group_user_prompt", "")
        LOGGER.info(f"调用工具参数: {tool_info.get('parameter',{})}")
        results = tool_module.run(tool_info.get('parameter',{}), last_message, group_user_prompt, group_history)
        
        LOGGER.info(f" user_tool_results = {results}")
        if type(results) == list:
            for result in results:
                LOGGER.info(f"\n\n{type(result)}\n{result}\n\n")
                if type(result) == str and result:
                    bot_manager.add_message_to_group_history("assistant", result, tool=tool_info)
                elif type(result) == dict and result and result.get("type") == 'call_bot':
                    function_call = result
                    bot_id = function_call.get("id")
                    bot = bot_manager.get_bot_by_id(bot_id)
                    LOGGER.info(f"\n\n即将调用的Bot为:\n{bot} {bot_id}\n\n")
                    if bot:
                        group_history = st.session_state.bot_manager.get_current_group_history()
                        if show_planning:
                            prompt = f'下一步从【{bot["name"]}】的视角思考：{function_call.get("prompt","")}'
                            bot_manager.add_message_to_group_history("assistant", prompt, tool=tool_info)

                            prompt = f'请你专注于你的角色设定，结合上下文继续讨论前面的话题，尽量言简意赅地表达最核心的信息和观点，格式清晰易读，尽量控制在200字以内。{prompt}'
                            if group_user_prompt:
                                prompt = f'{prompt}\n\n回复时的要求是：\n{group_user_prompt}'
                            response = get_response_from_bot_group(prompt, bot, group_history)
                        else:
                            response = get_response_from_bot_group(group_user_prompt, bot, group_history)
                        bot_manager.add_message_to_group_history("assistant", response, bot=bot)
                elif type(result) == dict and result and result.get("type") == 'call_tool':
                    function_call = result
                    tool_id = function_call.get("id")
                    tool = tool_manager.tool_map.get(tool_id)
                    LOGGER.info(f"\n\n即将调用的Tool为:\n{tool} {tool_id}\n\n")
                    if tool:
                        response = use_tool_once(tool_id)
                        LOGGER.info(f"\n\ntool输出为：\n{response}\n\n")
        elif type(results) == str:
            response = results
            bot_manager.add_message_to_group_history("assistant", response, tool=tool_info)
        else:
            bot_manager.add_message_to_group_history("assistant", '(奇怪，没有得到结果)', tool=tool_info)

    except Exception as e:
        error_msg = f"执行工具时出错: {str(e)}"
        LOGGER.error(error_msg)
        st.error(error_msg)
        bot_manager.add_message_to_group_history("assistant", f"工具执行失败: {str(e)}", tool=tool_info)

    st.rerun()
    