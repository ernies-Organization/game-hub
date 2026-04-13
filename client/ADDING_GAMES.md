# Adding Games

Each game lives in one module under `games/` and owns both:

- its Flet client screen
- its host-side room logic
- its optional in-room chat and spectator behavior

## Fast path

1. Copy `games/template_game.py` to a new file such as `games/connect4.py`.
2. Rename:
   - `TemplateRoom`
   - `TemplateGameScreen`
   - `GAME_DEFINITION`
   - the game `id` and `title`
3. Implement:
   - `add_player()`
   - `start()`
   - `handle_command()`
   - `build()`
   - `handle_server_line()`
4. Register the game in `core/game_registry.py`.

## Contract

Your module must export:

- `create_screen(page, on_back, settings, network, online)`
- `create_room()`
- `GAME_DEFINITION`

`GAME_DEFINITION` must be a `GameDefinition` with:

- `id`
- `title`
- `min_players`
- `max_players`
- `supports_offline`
- `supports_online`
- `create_screen`
- `create_room`

## Protocol tips

The shared line protocol supports:

- `HELLO <version>`
- `JOIN <game> <name>`
- `CHAT <message>`
- `MOVE <data>`
- `QUIT`

And server messages like:

- `VERSION <server_version>`
- `GAMES <game1,game2>`
- `MESSAGE <text>`
- `ERROR <text>`

You can also add game-specific messages, like Tic-Tac-Toe does with:

- `BOARD <data>`
- `TURN <player>`
- `RESULT <data>`

## Design rule

If a new game needs custom online behavior, put that behavior in the game module, not in `app.py`.

## Reusable room chat

`BaseRoom` already gives you:

- in-memory room chat history
- spectator storage
- `add_chat_message()`
- `send_chat_history()`
- `clear_chat()`

That means new games can support room chat without creating a separate chat app.
