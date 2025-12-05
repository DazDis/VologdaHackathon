import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import numpy as np
from collections import defaultdict


def parse_xml_log(xml_path):
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
        # Возвращаем оригинальное название для неизвестных языков
        return language_id.split('_')[0].upper() if '_' in language_id else language_id.upper()


def create_language_vectors(participants, submissions, df_total,
                            target_grade=None, target_municipality=None,
                            min_score=None, max_score=None, top_n=9):
    """Создание бинарных векторов использования языков программирования"""

    # Фильтрация участников по критериям
    filtered_participants = {}
    for uid, data in participants.items():
        # Проверяем класс
        grade_ok = (target_grade is None) or (data['grade'] == target_grade)

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
        print("Нет данных для выбранных критериев фильтрации.")
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
    df_vectors['name'] = df_vectors['user_id'].map(lambda x: participants[x]['name'])
    df_vectors['grade'] = df_vectors['user_id'].map(lambda x: participants[x]['grade'])
    df_vectors['municipality'] = df_vectors['user_id'].map(lambda x: participants[x]['municipality'])

    # Суммируем все векторы (получаем количество УНИКАЛЬНЫХ участников по каждому языку)
    language_sums = df_vectors[top_languages].sum()

    # Сортируем языки по количеству участников (по убыванию)
    language_sums = language_sums.sort_values(ascending=False)

    return df_vectors, language_sums, lang_to_index


def visualize_language_vectors(language_sums, total_participants, output_file='language_vectors.png'):
    """Визуализация результатов в виде диаграммы"""

    if language_sums.empty:
        print("Нет данных для визуализации.")
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
    plt.title('Количество участников по языкам программирования', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Язык программирования', fontsize=12)
    plt.ylabel('Количество уникальных участников', fontsize=12)

    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    # Добавляем информацию

    plt.tight_layout()

    # Сохраняем диаграмму
    plt.savefig(output_file, dpi=300, bbox_inches='tight')

    # Показываем диаграмму
    plt.show()

    return language_sums


def main():
    parser = argparse.ArgumentParser(description='Анализ использования языков программирования с векторами')
    parser.add_argument('--xml', default='log.xml', help='Путь к XML файлу с логами')
    parser.add_argument('--output', default='language_vectors.png', help='Путь для сохранения диаграммы')
    parser.add_argument('--grade', help='Фильтр по классу (например: 9, 10, 11)')
    parser.add_argument('--municipality', help='Фильтр по муниципалитету')
    parser.add_argument('--min-score', type=float, help='Минимальный балл участника')
    parser.add_argument('--max-score', type=float, help='Максимальный балл участника')
    parser.add_argument('--csv-output', default='language_vectors.csv', help='Путь для сохранения CSV с векторами')
    parser.add_argument('--show-vectors', action='store_true', help='Показать векторы участников')
    parser.add_argument('--top-n', type=int, default=9, help='Количество топ языков для анализа (по умолчанию: 9)')

    args = parser.parse_args()

    # Проверяем существование файла
    if not Path(args.xml).exists():
        print(f"Файл {args.xml} не найден.")
        return


    try:
        # Парсим XML
        participants, submissions = parse_xml_log(args.xml)

        # Получаем лучшие баллы участников
        df_total = get_best_scores(participants, submissions)

        # Создаем векторы языков
        df_vectors, language_sums, lang_to_index = create_language_vectors(
            participants=participants,
            submissions=submissions,
            df_total=df_total,
            target_grade=args.grade,
            target_municipality=args.municipality,
            min_score=args.min_score,
            max_score=args.max_score,
            top_n=args.top_n
        )

        if df_vectors is None:
            print("Не удалось создать векторы. Проверьте критерии фильтрации.")
            return

        # Выводим информацию о векторах
        total_participants = len(df_vectors)

        # Создаем визуализацию
        if not language_sums.empty:
            # Визуализируем
            result = visualize_language_vectors(language_sums, total_participants, args.output)


            for lang, count in language_sums.items():
                percentage = (count / total_participants) * 100

            # Суммируем все векторы
            sum_vector = language_sums.values


            # Показываем пример вектора

            for i, (_, row) in enumerate(df_vectors.head().iterrows()):
                vector = [row[lang] for lang in language_sums.index]
                vector_str = ''.join(str(int(v)) for v in vector)


            # Статистика по количеству языков на участника

            df_vectors['num_languages'] = df_vectors[language_sums.index].sum(axis=1)
            lang_stats = df_vectors['num_languages'].value_counts().sort_index()

            for num_langs, count in lang_stats.items():
                percentage = (count / total_participants) * 100


        # Сохраняем векторы в CSV
        df_vectors.to_csv(args.csv_output, sep=';', index=False, encoding='utf-8-sig')

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()