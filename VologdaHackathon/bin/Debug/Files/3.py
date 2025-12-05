import os
import csv
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def levenshtein_distance(s1, s2):
    """Расстояние Левенштейна (оптимизированная версия)"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def parse_submissions_from_xml(xml_path):
    """Парсинг всех submit событий из XML"""
    print(f"Парсинг XML: {xml_path}")
    
    submissions_by_user = {}
    
    try:
        # Используем итеративный парсинг для экономии памяти
        for event, elem in ET.iterparse(xml_path, events=('end',)):
            if elem.tag == 'submit':
                try:
                    user_id = elem.get('userId')
                    problem_id = elem.get('problemTitle')
                    submission_id = elem.get('id')
                    contest_time = int(elem.get('contestTime', 0))
                    score = float(elem.get('score', 0))
                    
                    if user_id not in submissions_by_user:
                        submissions_by_user[user_id] = {}
                    
                    if problem_id not in submissions_by_user[user_id]:
                        submissions_by_user[user_id][problem_id] = []
                    
                    submissions_by_user[user_id][problem_id].append({
                        'id': submission_id,
                        'time': contest_time,
                        'score': score,
                        'verdict': elem.get('verdict', ''),
                        'language': elem.get('languageId', '')
                    })
                    
                except (ValueError, TypeError) as e:
                    continue
                finally:
                    elem.clear()  # Освобождаем память
    
    except Exception as e:
        print(f"Ошибка парсинга XML: {e}")
    
    print(f"Найдено пользователей: {len(submissions_by_user)}")
    return submissions_by_user

def find_code_file(submission_id, code_dir):
    """Поиск файла с кодом по ID отправки"""
    for root, dirs, files in os.walk(code_dir):
        for file in files:
            # Ищем файл с submission_id в имени
            if submission_id in file and any(file.endswith(ext) for ext in ['.py', '.cpp', '.java', '.c', '.pas']):
                return os.path.join(root, file)
    return None

def read_file_content(filepath):
    """Чтение всего файла как текста"""
    if not filepath or not os.path.exists(filepath):
        return ""
    
    try:
        # Пробуем разные кодировки
        for encoding in ['utf-8', 'cp1251', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()
            except:
                continue
    except:
        pass
    
    return ""

def analyze_user_problem(user_id, problem_id, solutions, code_dir, min_score, speed_limit):
    """Анализ решений одной задачи одного пользователя"""
    results = []
    
    # Сортируем решения по времени
    sorted_solutions = sorted(solutions, key=lambda x: x['time'])
    
    for i in range(1, len(sorted_solutions)):
        current = sorted_solutions[i]
        previous = sorted_solutions[i-1]
        
        # Проверяем минимальный балл
        if current['score'] < min_score or previous['score'] < min_score:
            continue
        
        # Время между отправками в секундах
        time_diff = (current['time'] - previous['time']) / 1000.0
        
        # Находим файлы с кодом
        current_file = find_code_file(current['id'], code_dir)
        previous_file = find_code_file(previous['id'], code_dir)
        
        if not current_file:
            continue
        
        # Читаем содержимое файлов
        current_text = read_file_content(current_file)
        previous_text = read_file_content(previous_file) if previous_file else ""
        
        # Вычисляем расстояния Левенштейна
        l1 = levenshtein_distance(previous_text, current_text) if previous_text else float('inf')
        l2 = len(current_text)  # расстояние от пустой строки
        l = min(l1, l2)
        
        # Проверяем критерий плагиата
        allowed = speed_limit * time_diff
        
        if l > allowed:
            results.append({
                'user_id': user_id,
                'problem_id': problem_id,
                'prev_sub_id': previous['id'],
                'curr_sub_id': current['id'],
                'prev_score': previous['score'],
                'curr_score': current['score'],
                'prev_time': previous['time'],
                'curr_time': current['time'],
                'time_diff_sec': time_diff,
                'levenshtein': l,
                'allowed_speed': allowed,
                'excess': l - allowed,
                'prev_file': previous_file or "",
                'curr_file': current_file,
                'prev_verdict': previous['verdict'],
                'curr_verdict': current['verdict']
            })
    
    return results

def save_results_csv(results, output_path):
    """Сохранение результатов в CSV файл"""
    if not results:
        print("Нет данных для сохранения")
        return
    
    # Определяем заголовки
    fieldnames = [
        'user_id', 'problem_id', 'prev_submission_id', 'curr_submission_id',
        'prev_score', 'curr_score', 'prev_time_ms', 'curr_time_ms',
        'time_diff_seconds', 'levenshtein_distance', 'allowed_by_speed',
        'excess', 'prev_file_path', 'curr_file_path',
        'prev_verdict', 'curr_verdict'
    ]
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"Сохранено {len(results)} записей в {output_path}")
        
    except Exception as e:
        print(f"Ошибка при сохранении CSV: {e}")

def main():
    """Основная функция"""
    import sys
    
    # Конфигурация
    SPEED_LIMIT = 3  # символов в секунду
    MIN_SCORE = 101  # минимальный балл
    THREADS = 4      # количество потоков
    
    # Ввод параметров
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
        code_dir = sys.argv[2] if len(sys.argv) > 2 else input("Путь к папке с кодом: ")
    else:
        xml_file = input("Путь к XML файлу: ").strip()
        code_dir = input("Путь к папке с кодом: ").strip()
    
    if not os.path.exists(xml_file):
        print(f"Файл не найден: {xml_file}")
        return
    
    if not os.path.exists(code_dir):
        print(f"Папка не найдена: {code_dir}")
        return
    
    # Чтение XML
    start_time = time.time()
    submissions = parse_submissions_from_xml(xml_file)
    
    if not submissions:
        print("Нет данных для анализа")
        return
    
    # Подготовка задач для многопоточности
    print("\nАнализ решений...")
    all_results = []
    tasks = []
    
    for user_id, problems in submissions.items():
        for problem_id, solutions in problems.items():
            if len(solutions) >= 2:  # Нужно минимум 2 решения для сравнения
                tasks.append((user_id, problem_id, solutions))
    
    # Многопоточный анализ
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        
        for user_id, problem_id, solutions in tasks:
            future = executor.submit(
                analyze_user_problem,
                user_id, problem_id, solutions, code_dir, MIN_SCORE, SPEED_LIMIT
            )
            futures.append(future)
        
        # Сбор результатов
        for i, future in enumerate(as_completed(futures)):
            try:
                problem_results = future.result()
                if problem_results:
                    all_results.extend(problem_results)
                
                if (i + 1) % 100 == 0:
                    print(f"Обработано {i + 1}/{len(futures)} задач, найдено {len(all_results)} подозрительных")
                    
            except Exception as e:
                print(f"Ошибка при анализе задачи: {e}")
    
    # Вывод статистики
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("АНАЛИЗ ЗАВЕРШЕН")
    print(f"{'='*60}")
    print(f"Время выполнения: {elapsed:.2f} сек")
    print(f"Обработано пользователей: {len(submissions)}")
    print(f"Обработано задач: {len(tasks)}")
    print(f"Найдено подозрительных пар: {len(all_results)}")
    
    # Сохранение в CSV
    if all_results:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_file = f"suspicious_solutions_{timestamp}.csv"
        save_results_csv(all_results, csv_file)
        
        # Краткая статистика
        print(f"\nСтатистика подозрительных решений:")
        print(f"{'-'*60}")
        
        # Группировка по пользователям
        user_counts = {}
        for result in all_results:
            user_id = result['user_id']
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        # Топ-10 пользователей
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print("Топ-10 пользователей с подозрительными решениями:")
        for user_id, count in sorted_users:
            print(f"  {user_id}: {count} подозрительных пар")
        
        # Наибольшие превышения
        if all_results:
            sorted_by_excess = sorted(all_results, key=lambda x: x['excess'], reverse=True)[:5]
            print(f"\nТоп-5 наибольших превышений:")
            for result in sorted_by_excess:
                print(f"  User {result['user_id']}, Problem {result['problem_id']}: "
                      f"время={result['time_diff_sec']:.1f}с, "
                      f"превышение={result['excess']:.1f}")
    else:
        print("Подозрительных решений не найдено.")

if __name__ == "__main__":
    main()
