import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
from collections import defaultdict


def parse_xml_log(xml_path='log.xml'):
    """Парсинг XML файла и извлечение данных"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Словарь участников
    participants = {}
    for user in root.find('users'):
        uid = user.get('id')
        displayed_name = user.get('displayedName')

        # Разбираем строку: "Фамилия Имя, Класс, Муниципалитет"
        parts = [part.strip() for part in displayed_name.split(',')]

        if len(parts) >= 3:
            name = parts[0]
            grade = parts[1]
            municipality = parts[2]
        else:
            name = displayed_name
            grade = "Не указан"
            municipality = "Не указан"

        participants[uid] = {
            'name': name,
            'grade': grade,
            'municipality': municipality
        }

    # Собираем все отправки
    submissions = []
    for event in root.find('events'):
        if event.tag == 'submit':
            user_id = event.get('userId')
            problem_title = event.get('problemTitle')
            language_id = event.get('languageId')

            # Получаем баллы (если нет - 0)
            score_str = event.get('score')
            if score_str is None or score_str == '':
                score = 0.0
            else:
                try:
                    score = float(score_str)
                except ValueError:
                    score = 0.0

            # Добавляем отправку
            submissions.append({
                'user_id': user_id,
                'problem': problem_title,
                'language_id': language_id,
                'score': score
            })

    return participants, submissions


def get_best_scores(participants, submissions):
    """Получаем лучшие баллы участников по всем задачам"""
    df_submissions = pd.DataFrame(submissions)

    # Группируем по участнику и задаче, берём максимальный балл
    df_best = df_submissions.groupby(['user_id', 'problem'], as_index=False)['score'].max()

    # Суммируем баллы по участникам
    df_total = df_best.groupby('user_id', as_index=False)['score'].sum()
    df_total = df_total.rename(columns={'score': 'total_score'})

    # Добавляем информацию об участниках
    df_total['grade'] = df_total['user_id'].map(lambda x: participants[x]['grade'])
    df_total['municipality'] = df_total['user_id'].map(lambda x: participants[x]['municipality'])

    return df_total


def normalize_language(language_id):
    """Нормализация языков программирования - объединение компиляторов одного языка"""
    language_id = str(language_id).lower()

    # Группировка языков (на основе предоставленного XML)
    if 'python' in language_id or 'pypy' in language_id:
        return 'Python'
    elif 'cpp' in language_id or 'c++' in language_id:
        return 'C++'
    elif 'c#' in language_id or 'csharp' in language_id or 'dotnet' in language_id:
        return 'C#'
    elif 'java' in language_id or 'jdk' in language_id:
        return 'Java'
    elif 'pascal' in language_id or 'delphi' in language_id or 'fpc' in language_id or 'dcc' in language_id:
        return 'Pascal'
    elif 'go' in language_id or 'golang' in language_id:
        return 'Go'
    elif 'rust' in language_id:
        return 'Rust'
    elif 'kotlin' in language_id:
        return 'Kotlin'
    elif 'haskell' in language_id:
        return 'Haskell'
    else:
        return language_id.split('_')[0].upper() if '_' in language_id else language_id.upper()


def create_language_vectors(participants, submissions, df_total,
                            target_grade=None, target_municipality=None,
                            min_score=None, max_score=None, top_n=9):
    """Создание бинарных векторов использования языков программирования"""

    # Фильтрация участников по критериям
    filtered_participants = {}
    for uid, data in participants.items():
        # Проверяем класс
        grade_ok = (target_grade is None) or (str(data['grade']) == str(target_grade))

        # Проверяем муниципалитет
        municipality_ok = (target_municipality is None) or (data['municipality'] == target_municipality)

        if grade_ok and municipality_ok:
            filtered_participants[uid] = data

    # Получаем данные о баллах для отфильтрованных участников
    df_filtered_total = df_total[df_total['user_id'].isin(filtered_participants.keys())]

    # Фильтрация по диапазону баллов
    if min_score is not None:
        df_filtered_total = df_filtered_total[df_filtered_total['total_score'] >= min_score]
    if max_score is not None:
        df_filtered_total = df_filtered_total[df_filtered_total['total_score'] <= max_score]

    # Получаем список отфильтрованных user_id
    filtered_user_ids = set(df_filtered_total['user_id'].tolist())

    # Фильтруем отправки только от выбранных участников
    df_submissions = pd.DataFrame(submissions)
    df_filtered = df_submissions[df_submissions['user_id'].isin(filtered_user_ids)]

    if df_filtered.empty:
        return None, None, None

    # Сначала собираем все УНИКАЛЬНЫЕ языки для каждого участника
    user_unique_languages = defaultdict(set)
    language_counter = defaultdict(int)

    # Проходим по всем отправкам
    for _, row in df_filtered.iterrows():
        user_id = row['user_id']
        language_id = row['language_id']
        normalized_lang = normalize_language(language_id)

        # Добавляем язык в множество участника (set автоматически удаляет дубликаты)
        if normalized_lang not in user_unique_languages[user_id]:
            user_unique_languages[user_id].add(normalized_lang)
            language_counter[normalized_lang] += 1

    # Выбираем топ-N языков (по количеству УНИКАЛЬНЫХ участников)
    top_languages = [lang for lang, _ in sorted(language_counter.items(),
                                                key=lambda x: x[1], reverse=True)[:top_n]]

    # Создаем словарь для быстрого доступа по индексу
    lang_to_index = {lang: idx for idx, lang in enumerate(top_languages)}

    # Создаем бинарные векторы
    user_vectors = {}
    for user_id, languages in user_unique_languages.items():
        vector = [0] * len(top_languages)
        for lang in languages:
            if lang in lang_to_index:
                vector[lang_to_index[lang]] = 1
        user_vectors[user_id] = vector

    # Создаем DataFrame с векторами
    vectors_data = []
    for user_id, vector in user_vectors.items():
        vectors_data.append([user_id] + vector)

    columns = ['user_id'] + top_languages
    df_vectors = pd.DataFrame(vectors_data, columns=columns)

    # Добавляем информацию об участниках
    df_vectors['Имя'] = df_vectors['user_id'].map(lambda x: participants[x]['name'])
    df_vectors['Класс'] = df_vectors['user_id'].map(lambda x: participants[x]['grade'])
    df_vectors['Муниципалитет'] = df_vectors['user_id'].map(lambda x: participants[x]['municipality'])

    # Добавляем общий балл участника
    df_vectors['Общий_балл'] = df_vectors['user_id'].map(
        lambda x: df_filtered_total[df_filtered_total['user_id'] == x]['total_score'].iloc[0]
        if not df_filtered_total[df_filtered_total['user_id'] == x].empty else 0
    )

    # Переупорядочиваем столбцы
    column_order = ['Имя', 'Класс', 'Муниципалитет', 'Общий_балл'] + top_languages
    df_vectors = df_vectors[column_order]

    # Суммируем все векторы (получаем количество УНИКАЛЬНЫХ участников по каждому языку)
    language_sums = df_vectors[top_languages].sum()

    # Сортируем языки по количеству участников (по убыванию)
    language_sums = language_sums.sort_values(ascending=False)

    return df_vectors, language_sums, top_languages


def visualize_language_vectors(language_sums, total_participants, params, output_file='language_vectors.png'):
    """Визуализация результатов в виде диаграммы"""

    if language_sums.empty:
        return None

    # Создаем диаграмму
    plt.figure(figsize=(12, 8))

    # Цвета для столбцов
    colors = plt.cm.Set3(np.arange(len(language_sums)) / len(language_sums))

    bars = plt.bar(language_sums.index, language_sums.values, color=colors, edgecolor='black')

    # Добавляем значения над столбцами
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                 f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Настройка графика
    title = 'Количество участников по языкам программирования\n'

    # Добавляем информацию о фильтрах в заголовок
    subtitle_parts = []
    if params['grade']:
        subtitle_parts.append(f'Класс: {params["grade"]}')
    if params['municipality']:
        subtitle_parts.append(f'Муниципалитет: {params["municipality"]}')
    if params['min_score'] is not None or params['max_score'] is not None:
        min_score = params['min_score'] if params['min_score'] is not None else 0
        max_score = params['max_score'] if params['max_score'] is not None else '∞'
        subtitle_parts.append(f'Баллы: {min_score}-{max_score}')

    if subtitle_parts:
        title += ' | '.join(subtitle_parts)

    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Язык программирования', fontsize=12)
    plt.ylabel('Количество уникальных участников', fontsize=12)

    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', alpha=0.3, linestyle='--')



    # Сохраняем диаграмму
    plt.savefig(output_file, dpi=300, bbox_inches='tight')

    # Показываем диаграмму
    plt.show()

    return output_file


def save_to_csv(df_vectors, language_sums, params, base_filename='language_analysis'):
    """Сохранение результатов в CSV файлы"""

    if df_vectors is None or df_vectors.empty:
        return []

    # Создаем основную таблицу с участниками
    main_csv = f"{base_filename}_participants.csv"
    df_vectors.to_csv(main_csv, sep=';', index=False, encoding='utf-8-sig')

    # Создаем файл со статистикой по языкам
    stats_csv = f"{base_filename}_languages.csv"
    stats_data = []
    total_participants = len(df_vectors)

    for lang, count in language_sums.items():
        percentage = (count / total_participants) * 100 if total_participants > 0 else 0
        stats_data.append({
            'Язык программирования': lang,
            'Количество участников': int(count),
            'Доля участников (%)': round(percentage, 2)
        })

    df_stats = pd.DataFrame(stats_data)
    df_stats.to_csv(stats_csv, sep=';', index=False, encoding='utf-8-sig')

    # Создаем файл с параметрами анализа
    params_csv = f"{base_filename}_params.csv"
    params_data = [{
        'Параметр': 'Класс',
        'Значение': params['grade'] if params['grade'] else 'Все'
    }, {
        'Параметр': 'Муниципалитет',
        'Значение': params['municipality'] if params['municipality'] else 'Все'
    }, {
        'Параметр': 'Минимальный балл',
        'Значение': params['min_score'] if params['min_score'] is not None else 'Любой'
    }, {
        'Параметр': 'Максимальный балл',
        'Значение': params['max_score'] if params['max_score'] is not None else 'Любой'
    }, {
        'Параметр': 'Топ языков',
        'Значение': params['top_n']
    }, {
        'Параметр': 'Всего участников',
        'Значение': total_participants
    }, {
        'Параметр': 'Языков проанализировано',
        'Значение': len(language_sums)
    }, {
        'Параметр': 'Сумма элементов векторов',
        'Значение': int(language_sums.sum())
    }]

    df_params = pd.DataFrame(params_data)
    df_params.to_csv(params_csv, sep=';', index=False, encoding='utf-8-sig')

    return [main_csv, stats_csv, params_csv]


def get_user_input():
    """Получение параметров от пользователя"""
    # Проверяем существование файла
    if not Path('log.xml').exists():
        print("Ошибка: Файл log.xml не найден.")
        return None

    # Запрашиваем класс
    grade_input = input("Введите номер класса (9, 10, 11) или Enter для всех классов: ").strip()
    grade = int(grade_input) if grade_input.isdigit() else None

    # Запрашиваем муниципалитет
    municipality = input("Введите муниципалитет или Enter для всех: ").strip()
    municipality = municipality if municipality else None

    # Запрашиваем диапазон баллов
    print("\nДиапазон баллов участников:")
    min_score_input = input("Минимальный балл (или Enter для любого): ").strip()
    max_score_input = input("Максимальный балл (или Enter для любого): ").strip()

    min_score = float(min_score_input) if min_score_input.replace('.', '', 1).isdigit() else None
    max_score = float(max_score_input) if max_score_input.replace('.', '', 1).isdigit() else None

    # Запрашиваем количество языков для анализа
    top_n_input = input("\nСколько топ языков анализировать (по умолчанию 9): ").strip()
    top_n = int(top_n_input) if top_n_input.isdigit() else 9

    # Запрашиваем префикс для файлов
    output_prefix = input("\nВведите префикс для выходных файлов (по умолчанию 'analysis'): ").strip()
    if not output_prefix:
        output_prefix = 'analysis'

    # Собираем параметры
    params = {
        'grade': grade,
        'municipality': municipality,
        'min_score': min_score,
        'max_score': max_score,
        'top_n': top_n,
        'output_prefix': output_prefix
    }

    return params


def main():
    # Получаем параметры от пользователя
    params = get_user_input()
    if params is None:
        return

    try:
        # Парсим XML
        participants, submissions = parse_xml_log('log.xml')

        # Получаем лучшие баллы участников
        df_total = get_best_scores(participants, submissions)

        # Создаем векторы языков
        result = create_language_vectors(
            participants=participants,
            submissions=submissions,
            df_total=df_total,
            target_grade=params['grade'],
            target_municipality=params['municipality'],
            min_score=params['min_score'],
            max_score=params['max_score'],
            top_n=params['top_n']
        )

        if result[0] is None:
            print("Нет данных для выбранных критериев фильтрации.")
            return

        df_vectors, language_sums, top_languages = result

        total_participants = len(df_vectors)

        # Сохраняем в CSV
        csv_files = save_to_csv(df_vectors, language_sums, params, params['output_prefix'])

        # Создаем диаграмму
        diagram_file = f"{params['output_prefix']}_diagram.png"
        visualize_language_vectors(language_sums, total_participants, params, diagram_file)

    except Exception as e:
        print(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()