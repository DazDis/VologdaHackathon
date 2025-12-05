import xml.etree.ElementTree as ET
import pandas as pd
import argparse
from pathlib import Path


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
                'score': score
            })

    return participants, submissions


def create_results_table(participants, submissions, target_grade=None, target_municipality=None):
    """Создание итоговой таблицы результатов"""

    # Преобразуем в DataFrame
    df_submissions = pd.DataFrame(submissions)

    # Фильтрация участников по классу и муниципалитету
    filtered_participants = {}
    for uid, data in participants.items():
        grade_ok = (target_grade is None) or (data['grade'] == target_grade)
        municipality_ok = (target_municipality is None) or (data['municipality'] == target_municipality)

        if grade_ok and municipality_ok:
            filtered_participants[uid] = data

    # Фильтруем отправки только от выбранных участников
    df_filtered = df_submissions[df_submissions['user_id'].isin(filtered_participants.keys())]

    if df_filtered.empty:
        print("Нет данных для выбранных критериев фильтрации.")
        return pd.DataFrame()

    # Группируем по участнику и задаче, берём максимальный балл
    df_best = df_filtered.groupby(['user_id', 'problem'], as_index=False)['score'].max()

    # Разворачиваем таблицу (pivot) - участники в строках, задачи в столбцах
    df_pivot = df_best.pivot(index='user_id', columns='problem', values='score').fillna(0)

    # Сортируем задачи по номеру
    problem_columns = sorted(df_pivot.columns, key=lambda x: int(x))
    df_pivot = df_pivot[problem_columns]

    # Добавляем итоговую сумму баллов
    df_pivot['Итого'] = df_pivot.sum(axis=1)

    # Добавляем информацию об участниках
    df_pivot = df_pivot.reset_index()
    df_pivot['Участник'] = df_pivot['user_id'].map(lambda x: filtered_participants[x]['name'])
    df_pivot['Класс'] = df_pivot['user_id'].map(lambda x: filtered_participants[x]['grade'])
    df_pivot['Муниципалитет'] = df_pivot['user_id'].map(lambda x: filtered_participants[x]['municipality'])

    # Сортируем по итоговому баллу (по убыванию)
    df_pivot = df_pivot.sort_values(by='Итого', ascending=False)

    # Рассчитываем места с учетом совпадений баллов
    # Используем метод 'min' для одинаковых мест
    df_pivot['Место'] = df_pivot['Итого'].rank(method='min', ascending=False).astype(int)

    # Формируем окончательный порядок столбцов
    final_columns = ['Место', 'Участник', 'Класс', 'Муниципалитет'] + problem_columns + ['Итого']
    df_final = df_pivot[final_columns]

    # Переименовываем столбцы с задачами для красоты
    df_final = df_final.rename(columns={col: str(col) for col in problem_columns})

    # Сбрасываем индекс
    df_final = df_final.reset_index(drop=True)

    return df_final


def main():
    parser = argparse.ArgumentParser(description='Генерация итоговой таблицы олимпиады')
    parser.add_argument('--xml', default='log.xml', help='Путь к XML файлу с логами')
    parser.add_argument('--output', default='results.csv', help='Путь для сохранения CSV файла')
    parser.add_argument('--grade', help='Фильтр по классу (например: 9, 10, 11)')
    parser.add_argument('--municipality', help='Фильтр по муниципалитету')

    args = parser.parse_args()
    # Парсим XML
    participants, submissions = parse_xml_log(args.xml)

    # Создаем таблицу результатов
    df_results = create_results_table(
        participants,
        submissions,
        target_grade=args.grade,
        target_municipality=args.municipality
    )

    if df_results.empty:
        print("Таблица результатов пуста.")
        return

    # Сохраняем в CSV с разделителем ';'
    df_results.to_csv(args.output, sep=';', index=False, encoding='utf-8-sig')


if __name__ == "__main__":
    main()
