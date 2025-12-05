import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import numpy as np


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

    # Группировка языков
    if 'python' in language_id or 'pypy' in language_id:
        return 'Python'
    elif 'cpp' in language_id or 'c++' in language_id or 'clang' in language_id:
        return 'C++'
    elif 'c#' in language_id or 'csharp' in language_id:
        return 'C#'
    elif 'java' in language_id:
        return 'Java'
    elif 'pascal' in language_id or 'delphi' in language_id or 'fpc' in language_id:
        return 'Pascal'
    elif 'go' in language_id:
        return 'Go'
    elif 'rust' in language_id:
        return 'Rust'
    elif 'kotlin' in language_id:
        return 'Kotlin'
    elif 'c' in language_id and '++' not in language_id and '#' not in language_id:
        return 'C'
    elif 'javascript' in language_id or 'node' in language_id:
        return 'JavaScript'
    elif 'swift' in language_id:
        return 'Swift'
    else:
        # Возвращаем оригинальное название для неизвестных языков
        return language_id.split('_')[0].upper() if '_' in language_id else language_id.upper()


def create_language_chart(participants, submissions, df_total,
                          target_grade=None, target_municipality=None,
                          min_score=None, max_score=None, output_file='languages_chart.png'):
    """Создание диаграммы использования языков программирования"""

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
        return None

    # Нормализуем языки программирования
    df_filtered['language_normalized'] = df_filtered['language_id'].apply(normalize_language)

    # Подсчитываем количество отправок по каждому языку
    language_counts = df_filtered['language_normalized'].value_counts().sort_values(ascending=False)

    # Убираем языки с нулевым количеством отправок
    language_counts = language_counts[language_counts > 0]

    if language_counts.empty:
        print("Нет данных об использовании языков программирования.")
        return None

    # Создаем диаграмму
    plt.figure(figsize=(12, 8))

    # Цвета для столбцов
    colors = plt.cm.Set3(np.arange(len(language_counts)) / len(language_counts))

    bars = plt.bar(language_counts.index, language_counts.values, color=colors, edgecolor='black')

    # Добавляем значения над столбцами
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                 f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Настройка графика
    plt.title('Использование языков программирования участниками олимпиады', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Язык программирования', fontsize=12)
    plt.ylabel('Количество отправок решений', fontsize=12)

    # Добавляем информацию о фильтрах в заголовок
    subtitle_parts = []
    if target_grade:
        subtitle_parts.append(f'Класс: {target_grade}')
    if target_municipality:
        subtitle_parts.append(f'Муниципалитет: {target_municipality}')
    if min_score is not None or max_score is not None:
        score_range = f'Баллы: {min_score if min_score else "0"}-{max_score if max_score else "∞"}'
        subtitle_parts.append(score_range)

    if subtitle_parts:
        plt.suptitle(' | '.join(subtitle_parts), fontsize=10, y=0.95, color='gray')

    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', alpha=0.3, linestyle='--')

    # Добавляем информацию об общем количестве
    total_submissions = language_counts.sum()
    unique_users = len(filtered_user_ids)

    info_text = f'Всего отправок: {total_submissions}\nУникальных участников: {unique_users}\n'
    info_text += f'Участник мог использовать несколько языков\n(сумма столбцов может превышать количество участников)'

    plt.figtext(0.02, 0.02, info_text, fontsize=9,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.7))

    plt.tight_layout()

    # Сохраняем диаграмму
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Диаграмма сохранена в файл: {output_file}")

    # Показываем диаграмму
    plt.show()

    # Выводим таблицу с данными
    print("\nСтатистика использования языков программирования:")
    print("=" * 50)
    print(f"{'Язык':<20} {'Отправок':<10} {'Доля (%)':<10}")
    print("-" * 50)

    for lang, count in language_counts.items():
        percentage = (count / total_submissions) * 100
        print(f"{lang:<20} {count:<10} {percentage:.1f}")

    print("=" * 50)
    print(f"Всего отправок: {total_submissions}")
    print(f"Уникальных языков: {len(language_counts)}")

    return language_counts


def main():
    parser = argparse.ArgumentParser(description='Визуализация использования языков программирования')
    parser.add_argument('--xml', default='log.xml', help='Путь к XML файлу с логами')
    parser.add_argument('--output', default='languages_chart.png', help='Путь для сохранения диаграммы')
    parser.add_argument('--grade', help='Фильтр по классу (например: 9, 10, 11)')
    parser.add_argument('--municipality', help='Фильтр по муниципалитету')
    parser.add_argument('--min-score', type=float, help='Минимальный балл участника')
    parser.add_argument('--max-score', type=float, help='Максимальный балл участника')
    parser.add_argument('--list-languages', action='store_true', help='Показать список всех языков в логе')

    args = parser.parse_args()

    # Проверяем существование файла
    if not Path(args.xml).exists():
        print(f"Файл {args.xml} не найден.")
        return

    print(f"Чтение XML файла: {args.xml}")

    try:
        # Парсим XML
        participants, submissions = parse_xml_log(args.xml)

        print(f"Найдено участников: {len(participants)}")
        print(f"Найдено отправок решений: {len(submissions)}")

        # Получаем лучшие баллы участников
        df_total = get_best_scores(participants, submissions)

        # Если запрошен список языков
        if args.list_languages:
            df_submissions = pd.DataFrame(submissions)
            all_languages = df_submissions['language_id'].unique()
            normalized_languages = set(normalize_language(lang) for lang in all_languages)

            print("\nВсе языки программирования в логе:")
            print("=" * 50)
            for i, lang in enumerate(sorted(all_languages), 1):
                norm_lang = normalize_language(lang)
                print(f"{i:3}. {lang:<30} -> {norm_lang}")
            print(f"\nВсего уникальных языков в логе: {len(all_languages)}")
            print(f"После нормализации: {len(normalized_languages)} языков")
            return

        # Создаем диаграмму
        language_stats = create_language_chart(
            participants=participants,
            submissions=submissions,
            df_total=df_total,
            target_grade=args.grade,
            target_municipality=args.municipality,
            min_score=args.min_score,
            max_score=args.max_score,
            output_file=args.output
        )

        if language_stats is None:
            print("Не удалось создать диаграмму. Проверьте критерии фильтрации.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()