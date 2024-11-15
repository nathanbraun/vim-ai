import vim
from itertools import tee
import re
import datetime as dt

# import utils
plugin_root = vim.eval("s:plugin_root")
vim.command(f"py3file {plugin_root}/py/utils.py")

prompt, role_options = parse_prompt_and_role(vim.eval("l:prompt"))
config = normalize_config(vim.eval("l:config"))
config_options = {
    **config['options'],
    **role_options['options_default'],
    **role_options['options_chat'],
}
config_ui = config['ui']

def update_yaml_title(proposed_title):
    yaml_start_pattern = re.compile(r"^---$")
    yaml_end_pattern = re.compile(r"^---$")
    title_pattern = re.compile(r"title: (.+)")

    lines = vim.current.buffer[:]
    in_yaml_block = False
    for i, line in enumerate(lines):
        if not in_yaml_block and yaml_start_pattern.match(line):
            in_yaml_block = True
        elif in_yaml_block and yaml_end_pattern.match(line):
            break
        elif in_yaml_block and title_pattern.match(line):
            lines[i] = f"title: {proposed_title}"
            vim.current.buffer[i] = lines[i]
            break

def get_current_yaml_title():
    title_pattern = re.compile(r"^title: (.+)$")
    lines = vim.current.buffer[:]
    for line in lines:
        match = title_pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return None  # Return None if no title is found

def initialize_chat_window():

    yaml_header_template = vim.eval('get(g:, "aichat_yaml_header", "")')
    
    # Replace placeholders with actual values if needed
    today = dt.date.today()
    yaml_header = yaml_header_template.replace('%date%', str(today))

    lines = vim.eval('getline(1, "$")')

    # Check for YAML header and insert it if missing
    yaml_header_exists = yaml_header in lines
    start_line = 0 if yaml_header_exists else len(yaml_header.split('\n')) + 1
    contains_user_prompt = any('>>> user' in line for line in lines[start_line:])

    if not contains_user_prompt:
        # Insert the YAML header if it does not exist
        if not yaml_header_exists and yaml_header_template:
            vim.current.buffer[:0] = yaml_header.split('\n')

        # Insert the user prompt after YAML header or at the beginning

        user_prompt_line = start_line
        vim.current.buffer.append('>>> user', user_prompt_line)

        # Insert an empty line after the user prompt
        vim.current.buffer.append('', user_prompt_line + 1)

        # Move the cursor to the empty line after the user prompt
        vim.current.window.cursor = (user_prompt_line + 2, 0)  # Line numbers are 1-indexed in Vim

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
        vim.command("normal! i" + prompt)
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
        url = options['endpoint_url']
        response = openai_request(url, request, http_options)
        def map_chunk(resp):
            printDebug("[chat] response: {}", resp)
            return resp['choices'][0]['delta'].get('content', '')
        text_chunks = map(map_chunk, response)

        current_title = get_current_yaml_title()
        if current_title == 'Untitled':

            search_iter, render_iter = tee(text_chunks, 2)
            accumulated_text = ""

            # search_iter = list(search_iter)
            proposed_title_pattern = re.compile(r"Proposed Title: ([^\n]+)")

            # print(search_iter)
            for text_chunk in search_iter:
                # print(text_chunk)
                accumulated_text += text_chunk
                if '\n\n' in accumulated_text:
                    # Extract the proposed title from the accumulated text
                    match = proposed_title_pattern.search(accumulated_text)
                    if match:
                        proposed_title = match.group(1).strip()
                        update_yaml_title(proposed_title)  # Call the function to update the YAML title
                        break  # Once we found the title, we can stop accumulating text

            render_text_chunks(render_iter, is_selection)
        else:
            render_text_chunks(text_chunks, is_selection)

        vim.command("normal! a\n\n>>> user\n\n")
        vim.command("redraw")
        clear_echo_message()
except BaseException as error:
    handle_completion_error(error)
    printDebug("[chat] error: {}", traceback.format_exc())
