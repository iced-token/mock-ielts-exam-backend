from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView
from datetime import timedelta
from .models import ListeningTest, ReadingTest, WritingTest, Exam, UserExamSession, TestResult
from django.utils import timezone
from django.db.models import Q
from .serializers import (
    ListeningTestSerializer, ReadingTestSerializer,
    WritingTestSerializer, ExamSerializer, UserExamSessionSerializer
)
from .permissions import IsAdminOrReadOnly, IsUserInExam, IsExamNotOver
from rest_framework.permissions import IsAuthenticated


class ListeningTestViewSet(viewsets.ModelViewSet):
    queryset = ListeningTest.objects.all()
    serializer_class = ListeningTestSerializer
    permission_classes = [IsAdminUser]


class ReadingTestViewSet(viewsets.ModelViewSet):
    queryset = ReadingTest.objects.all()
    serializer_class = ReadingTestSerializer
    permission_classes = [IsAdminUser]


class WritingTestViewSet(viewsets.ModelViewSet):
    queryset = WritingTest.objects.all()
    serializer_class = WritingTestSerializer
    permission_classes = [IsAdminUser]


class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [IsAdminOrReadOnly]

    def list(self, *args, **kwargs):
        queryset = self.queryset
        queryset = queryset.filter(Q(allowed_users__pk=self.request.user.pk) | Q(is_public=True))
        queryset = queryset.exclude(joined_users__pk=self.request.user.pk)
        queryset = queryset.exclude(finished_users__pk=self.request.user.pk)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='session', permission_classes=[IsAuthenticated])
    def my_session(self, request, *args, **kwargs):
        exam = self.get_queryset().get(pk=kwargs.pop('pk'))
        user = request.user
        try:
            session = UserExamSession.objects.get(user=user, exam=exam)
            serializer = UserExamSessionSerializer(session)
            return Response(serializer.data)
        except UserExamSession.DoesNotExist:
            return Response({ "detail": "You do not have a session for this exam" }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='joined-exams', permission_classes=[IsAuthenticated])
    def show_exams_user_joined(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = queryset.filter(joined_users__pk=request.user.pk)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='finished-exams', permission_classes=[IsAuthenticated])
    def show_exams_user_finished(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = queryset.filter(finished_users__pk=request.user.pk)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="join", permission_classes=[IsAuthenticated])
    def join_exam(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user

        if exam.end_time < timezone.now():
            return Response({"detail": "exam already ended"}, status=status.HTTP_400_BAD_REQUEST)

        if not exam.is_public and user not in exam.allowed_users.all():
            return Response({"detail": "You are not allowed"}, status=status.HTTP_400_BAD_REQUEST)
        
        exam.joined_users.add(user)
        return Response({"detail": "Successfully joined the exam."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='leave', permission_classes=[IsAuthenticated, IsUserInExam])
    def leave_exam(self, request, *args, **kwargs):
        exam = self.get_object()
        exam.joined_users.remove(request.user)
        return Response({"detail": "You left the exam."})

    @action(detail=True, methods=['post'], url_path='start-listening', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def start_listening(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user

        if exam.start_time > timezone.now():
            raise PermissionDenied('not the right time')

        if not UserExamSession.objects.filter(exam=exam, user=user).exists():
            UserExamSession.objects.create(exam=exam, user=user, listening_started_at=timezone.now())

        serializer = ListeningTestSerializer(exam.listening, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='finish-listening', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def finish_listening(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user
        answers = request.data

        try:
            session = UserExamSession.objects.get(exam=exam, user=user)
            if session.listening_finished:
                raise PermissionDenied("listening already finished")

            data = { "user": user, "exam": exam, "test_type": 'listening', "answers": answers }
            if timezone.now() - session.listening_started_at > timedelta(minutes=32):
                data['auto_failed'] = True

            TestResult.objects.create(**data)
            session.listening_finished = True
            session.save()
            return Response({"detail": "Congratulations! Go on now to reading!"})
        except UserExamSession.DoesNotExist:
            raise PermissionDenied("did you even start listening?")

    @action(detail=True, methods=['post'], url_path='start-reading', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def start_reading(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user

        try:
            session = UserExamSession.objects.get(exam=exam, user=user)
            if session.reading_finished:
                raise PermissionDenied("you have already finished reading")
            if not session.listening_finished:
                raise PermissionDenied("you haven't finished listening")
            if not session.reading_started_at:
                session.reading_started_at = timezone.now()
                session.save()

        except UserExamSession.DoesNotExist:
            raise PermissionDenied("listening not started")

        serializer = ReadingTestSerializer(exam.reading, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='finish-reading', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def finish_reading(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user
        answers = request.data

        try:
            session = UserExamSession.objects.get(exam=exam, user=user)
            if session.reading_finished:
                raise PermissionDenied("reading already finished")

            data = { "user": user, "exam": exam, "test_type": 'reading', "answers": answers }
            if timezone.now() - session.reading_started_at > timedelta(minutes=60):
                data['auto_failed'] = True

            TestResult.objects.create(**data)
            session.reading_finished = True
            session.save()
            return Response({"detail": "Congratulations! Go on now to writing!"})
        except UserExamSession.DoesNotExist:
            raise PermissionDenied("did you even start listening?")

    @action(detail=True, methods=['post'], url_path='start-writing', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def start_writing(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user

        try:
            session = UserExamSession.objects.get(exam=exam, user=user)
            if not session.reading_finished:
                raise PermissionDenied("you haven't finished reading")

            if not session.writing_started_at:
                session.writing_started_at = timezone.now()
                session.save()
        except UserExamSession.DoesNotExist:
            raise PermissionDenied("exam session has not been started, first start listening")

        serializer = WritingTestSerializer(exam.writing, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='finish-writing', permission_classes=[IsAuthenticated, IsUserInExam, IsExamNotOver])
    def finish_writing(self, request, *args, **kwargs):
        exam = self.get_object()
        user = request.user
        answers = request.data

        try:
            session = UserExamSession.objects.get(exam=exam, user=user)
            if session.writing_finished:
                raise PermissionDenied("writing already finished")

            data = { "user": user, "exam": exam, "test_type": 'writing', "answers": answers }
            if timezone.now() - session.writing_started_at > timedelta(minutes=60):
                data['auto_failed'] = True

            TestResult.objects.create(**data)
            exam.joined_users.remove(user)
            exam.finished_users.add(user)
            session.writing_finished = True
            session.save()
            return Response({"detail": "That's it! Just wait for the results!"})
        except UserExamSession.DoesNotExist:
            raise PermissionDenied("did you even start writing?")

class ReviewMyExamApiView(APIView):

    def round_band_score(self, score):
        if score % 1 > 0.5:
            return score - (score%1) + 1
        elif score % 1 < 0.5 and score % 1 > 0:
            return score - (score%1) + 0.5
        return score

    def review_answers(self, user_answers, correct_answers):
        total = 0
        for question, answers in correct_answers.items():
            try:
                if user_answers[question].lower() in answers: total += 1
            except: pass
        score = 9 * (total / 40)
        score = self.round_band_score(score)
        return score

    def get(self, request, *args, **kwargs):
        exam = Exam.objects.get(pk=kwargs.get('pk'))
        user = request.user
        results = TestResult.objects.filter(exam=exam, user=user)
        band_scores = []
        overall = 0

        for result in results:
            obj = { 'type': result.test_type }
            if result.test_type == 'writing':
                obj['score'] = 7.0
            elif result.test_type == 'listening':
                obj['score'] = self.review_answers(result.answers, exam.listening.answers)
            elif result.test_type == 'reading':
                obj['score'] = self.review_answers(result.answers, exam.reading.answers)
            overall += obj['score']
            band_scores.append(obj)

        band_scores.append({ 
            'type': 'overall',
            'score': self.round_band_score(overall/len(band_scores))
        })            

        return Response(band_scores)
