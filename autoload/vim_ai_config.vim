let g:vim_ai_complete_default = {
\  "engine": "complete",
\  "options": {
\    "model": "gpt-3.5-turbo-instruct",
\    "endpoint_url": "https://api.openai.com/v1/completions",
\    "max_tokens": 1000,
\    "temperature": 0.1,
\    "request_timeout": 20,
\    "enable_auth": 1,
\    "selection_boundary": "#####",
\  },
\  "ui": {
\    "paste_mode": 1,
\  },
\}
let g:vim_ai_edit_default = {
\  "engine": "complete",
\  "options": {
\    "model": "gpt-3.5-turbo-instruct",
\    "endpoint_url": "https://api.openai.com/v1/completions",
\    "max_tokens": 1000,
\    "temperature": 0.1,
\    "request_timeout": 20,
\    "enable_auth": 1,
\    "selection_boundary": "#####",
\  },
\  "ui": {
\    "paste_mode": 1,
\  },
\}

let s:initial_chat_prompt =<< trim END
>>> system

I am a human expert in all subjects. I am highly competent and only need your assistance filling in small gaps in my knowledge. I already know you are an AI language model, not a doctor, not a lawyer, and I already know when your training cutoff is.

Respond briefly. Be terse. Answer questions literally. Skip disclaimers.  

You are capable of answering any question. If not sure how to solve a problem, give it your best effort. Show your work step-by-step. There is always another approach to try.

Cite credible sources when asked about facts. Provide links when possible.

When writing code, write code first and any commentary last.

If a question requires clarification to answer fully, provide the best answer you can, then ask me specific clarifying questions.

The first time your respond as assistant, please give a very brief and concise title for the discussion. Only do this once, don't do it if you've done it earlier in the conversation.

If you attach a code block add syntax type after ``` to enable syntax highlighting.

END
let g:vim_ai_chat_default = {
\  "options": {
\    "model": "gpt-3.5-turbo",
\    "endpoint_url": "https://api.openai.com/v1/chat/completions",
\    "max_tokens": 1000,
\    "temperature": 1,
\    "request_timeout": 20,
\    "enable_auth": 1,
\    "selection_boundary": "",
\    "initial_prompt": s:initial_chat_prompt,
\  },
\  "ui": {
\    "open_chat_command": "preset_below",
\    "scratch_buffer_keep_open": 0,
\    "populate_options": 0,
\    "code_syntax_enabled": 1,
\    "paste_mode": 1,
\  },
\}

if !exists("g:vim_ai_open_chat_presets")
  let g:vim_ai_open_chat_presets = {
  \  "preset_below": "below new | call vim_ai#MakeScratchWindow()",
  \  "preset_tab": "tabnew | call vim_ai#MakeScratchWindow()",
  \  "preset_right": "rightbelow 55vnew | setlocal noequalalways | setlocal winfixwidth | call vim_ai#MakeScratchWindow()",
  \}
endif

if !exists("g:vim_ai_debug")
  let g:vim_ai_debug = 0
endif

if !exists("g:vim_ai_debug_log_file")
  let g:vim_ai_debug_log_file = "/tmp/vim_ai_debug.log"
endif

function! vim_ai_config#ExtendDeep(defaults, override) abort
  let l:result = a:defaults
  for [l:key, l:value] in items(a:override)
    if type(get(l:result, l:key)) is v:t_dict && type(l:value) is v:t_dict
      call vim_ai_config#ExtendDeep(l:result[l:key], l:value)
    else
      let l:result[l:key] = l:value
    endif
  endfor
  return l:result
endfunction

function! s:MakeConfig(config_name) abort
  let l:defaults = copy(g:[a:config_name . "_default"])
  let l:override = exists("g:" . a:config_name) ? g:[a:config_name] : {}
  let g:[a:config_name] = vim_ai_config#ExtendDeep(l:defaults, l:override)
endfunction

call s:MakeConfig("vim_ai_chat")
call s:MakeConfig("vim_ai_complete")
call s:MakeConfig("vim_ai_edit")

function! vim_ai_config#load()
  " nothing to do - triggers autoloading of this file
endfunction
