# Проверка toolchain финального артефакта

Текущий source SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` строго собран Apple Clang 17.0.0 с `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`. Полный open15: `29.789717928594 / 32.1`.

Ранее проверявшийся `g++` является драйвером Apple Clang, не GNU GCC; GCC 14.2 отсутствует. Настоящая сборка на GCC 14.2 не подтверждена.
