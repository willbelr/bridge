"This example make use of both xterm and urxvt terminals.
"You'll have to modify the terminals commands and the bridge.py location according to your favorite configuration.

"Execute/Upload current file
function! Run()
  let ext = expand('%:e')
  if ext == ""
    !killall xterm; xterm -hold -e bash -c %:p &
  elseif ext == "py"
    !killall xterm; xterm -hold -e python %:p &
  elseif ext == "ino"
    !urxvt --hold -e /usr/bin/python3 ~/scripts/bridge/bridge.py --upload %:p &
  endif
endfunction
noremap <F1> :w <bar> call Run()<CR><CR>

"Toggle serial monitor
function! Serial_monitor()
  let ext = expand('%:e')
  let is_running = system('ps aux | grep python | grep bridge.py | grep -v bash')
  if ext == "ino" || ext == "cpp" || ext == "py"
    if is_running == ''
      !/usr/bin/python3 ~/scripts/bridge/bridge.py --open %:p &> /dev/null & disown
    else
      !kill $(ps aux | grep python | grep bridge.py | awk '{ print $2 }')
    endif
  endif
endfunction
noremap <F2> :call Serial_monitor()<CR><CR>
