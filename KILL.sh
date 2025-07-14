#!/bin/bash

for session in $(tmux list-sessions -F '#S'); do
  for window in $(tmux list-windows -t "$session" -F '#I'); do
    for pane in $(tmux list-panes -t "$session:$window" -F '#P'); do
      echo "Sending Ctrl+C to $session:$window.$pane"
      tmux send-keys -t "$session:$window.$pane" C-c
    done
  done
done

tmux kill-session -t BIC
