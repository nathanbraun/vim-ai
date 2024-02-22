import vim
import re
import datetime as dt

# import utils
plugin_root = vim.eval("s:plugin_root")
vim.command(f"py3file {plugin_root}/py/utils.py")

config = normalize_config(vim.eval("l:config"))
config_options = config['options']
config_ui = config['ui']
prompt = vim.eval("l:prompt").strip()

def initialize_chat_window():
    lines = vim.eval('getline(1, "$")')

    # Check for YAML header and insert it if missing
    yaml_header_exists = False
    yaml_header_pattern = re.compile(r'^---\ntitle: .*?\ndate: .*?\ntags:.*?\n---', re.DOTALL)
    if yaml_header_pattern.search('\n'.join(lines)):
        yaml_header_exists = True

    if not yaml_header_exists:
        # Insert YAML header at the top of the file
        today = dt.datetime.now().strftime('%Y-%m-%d')
        yaml_header = f"---\ntitle: Untitled\ndate: {today}\ntags: [aichat]\n---\n"
        vim.current.buffer[:0] = yaml_header.split('\n')  # Prepend header
    
    # Find the position to start the chat content
    start_line = 1 if yaml_header_exists else len(yaml_header.split('\n'))
    
    # Now continue with the rest of the chat window initialization

    contains_user_prompt = any('>>> user' in line for line in lines[start_line:])
    if not contains_user_prompt:
        # If '>>> user' is not found, insert it after the YAML header
        vim.current.buffer.append('>>> user', start_line)

        # # user role not found, put whole file content as an user prompt
        # vim.command("normal! gg")
        # populates_options = config_ui['populate_options'] == '1'
        # if populates_options:
        #     vim.command("normal! O[chat-options]")
        #     vim.command("normal! o")
        #     for key, value in config_options.items():
        #         if key == 'initial_prompt':
        #             value = "\\n".join(value)
        #         vim.command("normal! i" + key + "=" + value + "\n")
        # vim.command("normal! " + ("o" if populates_options else "O"))
        # vim.command("normal! i>>> user\n")

    vim.command("normal! G")
    vim_break_undo_sequence()
    vim.command("redraw")

    file_content = vim.eval('trim(join(getline(1, "$"), "\n"))')
    role_lines = re.findall(r'(^>>> user|^>>> system|^<<< assistant).*', file_content, flags=re.MULTILINE)
    if not role_lines[-1].startswith(">>> user"):
        # last role is not user, most likely completion was cancelled before
        vim.command("normal! o")
        vim.command("normal! i\n>>> user\n\n")

    if prompt:
        vim.command("normal! a" + prompt)
        vim_break_undo_sequence()
        vim.command("redraw")

initialize_chat_window()

chat_options = parse_chat_header_options()
options = {**config_options, **chat_options}
openai_options = make_openai_options(options)
http_options = make_http_options(options)

initial_prompt = '\n'.join(options.get('initial_prompt', []))
initial_messages = parse_chat_messages(initial_prompt)

chat_content = vim.eval('trim(join(getline(1, "$"), "\n"))')
chat_messages = parse_chat_messages(chat_content)
is_selection = vim.eval("l:is_selection")

messages = initial_messages + chat_messages

try:
    if messages[-1]["content"].strip():
        vim.command("normal! Go\n<<< assistant\n\n")
        vim.command("redraw")

        print('Answering...')
        vim.command("redraw")

        request = {
            'stream': True,
            'messages': messages,
            **openai_options
        }
        printDebug("[chat] request: {}", request)
        url = config_options['endpoint_url']
        response = openai_request(url, request, http_options)
        def map_chunk(resp):
            printDebug("[chat] response: {}", resp)
            return resp['choices'][0]['delta'].get('content', '')
        text_chunks = map(map_chunk, response)
        render_text_chunks(text_chunks, is_selection)

        vim.command("normal! a\n\n>>> user\n\n")
        vim.command("redraw")
        clear_echo_message()
except BaseException as error:
    handle_completion_error(error)
    printDebug("[chat] error: {}", traceback.format_exc())
