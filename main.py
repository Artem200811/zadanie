import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

@dataclass
class ClassEvent:
    """Представляет одно занятие (пару)."""
    date: date
    period: int

@dataclass
class CourseInfo:
    """Хранит информацию о дисциплине и её расписании."""
    discipline_name: str
    group_number: str
    semester_start: date
    semester_end: date
    schedule: List[ClassEvent]

def parse_date(date_str: str, reference_year: int) -> date:
    """
    Парсит строку с датой. Поддерживает форматы 'YYYY-MM-DD' и 'DD.MM'.
    Для формата 'DD.MM' автоматически подставляется год из reference_year.
    """
    date_str = date_str.strip()
    try:
        # Попытка парсинга полного формата
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            # Попытка парсинга короткого формата с добавлением года
            return datetime.strptime(f"{date_str}.{reference_year}", "%d.%m.%Y").date()
        except ValueError:
            raise ValueError(f"Неверный формат даты: '{date_str}'. Ожидалось 'YYYY-MM-DD' или 'DD.MM'")

def load_schedule(file_path: str) -> CourseInfo:
    """
    Загружает и валидирует данные расписания из JSON-файла.
    """
    path = Path(file_path)
    if not path.exists():
        logging.error(f"Файл расписания не найден: {file_path}")
        raise FileNotFoundError(f"Файл '{file_path}' не существует.")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка парсинга JSON в файле {file_path}: {e}")
        raise ValueError(f"Некорректный формат JSON в файле: {e}")

    try:
        ref_year = datetime.strptime(data['semester_start'], "%Y-%m-%d").year
        
        schedule = []
        for item in data['schedule']:
            event_date = parse_date(item['date'], ref_year)
            schedule.append(ClassEvent(date=event_date, period=item['period']))
            
            # Предупреждение в лог, если пара выпадает на выходной (суббота=5, воскресенье=6)
            if event_date.weekday() >= 5:
                logging.warning(f"Занятие '{data['discipline_name']}' выпадает на выходной: {event_date}")

        return CourseInfo(
            discipline_name=data['discipline_name'],
            group_number=data['group_number'],
            semester_start=datetime.strptime(data['semester_start'], "%Y-%m-%d").date(),
            semester_end=datetime.strptime(data['semester_end'], "%Y-%m-%d").date(),
            schedule=schedule
        )
    except KeyError as e:
        logging.error(f"Отсутствует обязательное поле в JSON: {e}")
        raise ValueError(f"Неполные данные в файле расписания. Отсутствует поле: {e}")
    except ValueError as e:
        logging.error(f"Ошибка валидации данных: {e}")
        raise

def calculate_statistics(course: CourseInfo, current_date: date) -> Dict[str, Any]:
    """
    Вычисляет статистику по парам на основе текущей даты.
    """
    total_classes = len(course.schedule)
    
    # Пара считается "прошедшей", если её дата строго меньше текущей даты
    # (или можно использовать <=, если считать, что пара в текущий день уже прошла)
    # Для надёжности используем < current_date.
    passed_classes = sum(1 for event in course.schedule if event.date < current_date)
    
    remaining_classes = total_classes - passed_classes
    
    if total_classes > 0:
        completion_percentage = (passed_classes / total_classes) * 100
    else:
        completion_percentage = 0.0

    return {
        "total": total_classes,
        "passed": passed_classes,
        "remaining": remaining_classes,
        "percentage": completion_percentage
    }

def generate_report(course: CourseInfo, stats: Dict[str, Any]) -> str:
    """Формирует текстовый отчёт для вывода."""
    report = (
        f"Дисциплина: {course.discipline_name}\n"
        f"Группа: {course.group_number}\n"
        f"Всего пар: {stats['total']}\n"
        f"Прошло пар: {stats['passed']}\n"
        f"Осталось пар: {stats['remaining']}\n"
        f"Процент выполнения: {stats['percentage']:.2f}%"
    )
    return report

def save_report(report: str, output_file: str = "reminder.txt") -> None:
    """Сохраняет отчёт в файл."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logging.info(f"Отчёт успешно сохранён в {output_file}")
    except IOError as e:
        logging.error(f"Ошибка записи в файл {output_file}: {e}")
        print(f"Критическая ошибка: не удалось сохранить отчёт в {output_file}")

def main():
    """Основная точка входа в программу."""
    logging.info("--- Запуск программы подсчёта пар ---")
    
    schedule_file = "schedule.json"
    output_file = "reminder.txt"
    
    # Использование текущей даты (в соответствии с системным временем: 12 июня 2026 г.)
    today = date.today()
    logging.info(f"Текущая дата расчёта: {today}")

    try:
        # 1. Загрузка данных
        course = load_schedule(schedule_file)
        logging.info(f"Данные успешно загружены для дисциплины: {course.discipline_name}")

        # 2. Расчёт статистики
        stats = calculate_statistics(course, today)

        # 3. Генерация и вывод отчёта
        report = generate_report(course, stats)
        
        print("\n" + "="*40)
        print(report)
        print("="*40 + "\n")

        # 4. Сохранение в файл
        save_report(report, output_file)
        print(f"Данные также сохранены в файл: {output_file}")

    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"Ошибка при выполнении программы: {e}")
        sys.exit(1)
    except Exception as e:
        logging.exception("Произошла непредвиденная ошибка")
        print("Произошла внутренняя ошибка программы. Проверьте файл app.log.")
        sys.exit(1)
    finally:
        logging.info("--- Завершение работы программы ---\n")

if __name__ == "__main__":
    main()
